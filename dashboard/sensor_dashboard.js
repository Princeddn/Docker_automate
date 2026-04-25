const express = require('express');
const bodyParser = require('body-parser');
const Database = require('better-sqlite3');
const axios = require('axios');
const path = require('path');

const app = express();
const port = 3000;

// CONFIGURATION (Utilise les variables d'environnement pour le Cloud)
const CHIRPSTACK_API_KEY = process.env.CHIRPSTACK_API_KEY || 'REDACTED_JWT_PARTIAL';
const CHIRPSTACK_URL = process.env.CHIRPSTACK_URL || 'http://192.168.3.100:8081';

// Base de données SQLite
const db = new Database('history.db');
db.exec("CREATE TABLE IF NOT EXISTS measurements (id INTEGER PRIMARY KEY AUTOINCREMENT, dev_eui TEXT, name TEXT, sensor_data JSON, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)");

app.use(bodyParser.json());
app.use(express.static('public'));

// 1. Webhook : Réception des données de ChirpStack
app.post('/webhook', (req, res) => {
    const payload = req.body;

    // On vérifie qu'il s'agit d'un événement d'uplink
    if (payload.event === 'up') {
        const devEui = payload.deviceInfo.devEui;
        const devName = payload.deviceInfo.deviceName;
        const object = payload.object; // Données décodées par le Codec ChirpStack

        console.log(`[UPLINK] Reçu de ${devName} (${devEui}) :`, object);

        // Sauvegarde en base de données
        const stmt = db.prepare("INSERT INTO measurements (dev_eui, name, sensor_data) VALUES (?, ?, ?)");
        stmt.run(devEui, devName, JSON.stringify(object));
    }

    res.sendStatus(200);
});

// 2. API : Récupérer l'historique
app.get('/api/history', (req, res) => {
    const rows = db.prepare("SELECT * FROM measurements ORDER BY timestamp DESC LIMIT 50").all();
    res.json(rows.map(row => ({
        ...row,
        sensor_data: JSON.parse(row.sensor_data)
    })));
});

// 3. API : Envoyer un Downlink
app.post('/api/downlink', async (req, res) => {
    const { devEui, hexPayload } = req.body;

    try {
        const response = await axios.post(`${CHIRPSTACK_URL}/api/devices/${devEui}/queue`, {
            deviceQueueItem: {
                confirmed: false,
                data: Buffer.from(hexPayload, 'hex').toString('base64'),
                fPort: 10
            }
        }, {
            headers: { 'Authorization': `Bearer ${CHIRPSTACK_API_KEY}` }
        });
        res.json({ success: true, data: response.data });
    } catch (error) {
        console.error('Erreur Downlink:', error.response ? error.response.data : error.message);
        res.status(500).json({ success: false, error: 'Erreur lors de l\'envoi du downlink' });
    }
});

// 4. UI : Dashboard principal
app.get('/', (req, res) => {
    res.send(`
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Nexelec LoRa Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0f172a;
            --card: rgba(30, 41, 59, 0.7);
            --primary: #38bdf8;
            --accent: #818cf8;
        }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            color: white;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1000px; margin: auto; }
        h1 { font-weight: 300; letter-spacing: 2px; text-transform: uppercase; text-align: center; margin-bottom: 40px; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        
        .card {
            background: var(--card);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            transition: transform 0.3s ease;
        }
        .card:hover { transform: translateY(-5px); }

        .status-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; background: #22c55e; margin-right: 10px; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th { text-align: left; opacity: 0.6; font-size: 0.8rem; padding-bottom: 10px; }
        td { padding: 12px 0; border-top: 1px solid rgba(255,255,255,0.1); font-size: 0.9rem; }
        
        .value { color: var(--primary); font-weight: 600; }
        
        .downlink-btn {
            background: linear-gradient(90deg, var(--primary), var(--accent));
            border: none;
            color: white;
            padding: 10px 20px;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 600;
            margin-top: 10px;
            width: 100%;
        }
        .downlink-btn:active { transform: scale(0.98); }
        
        .timestamp { font-size: 0.7rem; opacity: 0.5; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Nexelec Sensor Health</h1>
        
        <div class="grid">
            <!-- Section Real-time View -->
            <div class="card">
                <h3>Dernière Activité</h3>
                <div id="live-data">Chargement...</div>
            </div>
            
            <!-- Section Downlink -->
            <div class="card">
                <h3>Command Center</h3>
                <p style="font-size: 0.8rem; opacity: 0.7;">Envoyer un signal LED au capteur (0101)</p>
                <input type="text" id="devEui" placeholder="DevEUI du capteur" style="width: 100%; margin-bottom: 10px; padding: 8px; border-radius: 5px; border: none; background: rgba(0,0,0,0.3); color: white;">
                <button class="downlink-btn" onclick="sendDownlink()">Envoyer Flash LED (HEX: 0101)</button>
            </div>
        </div>

        <!-- Section Historique -->
        <div class="card" style="margin-top: 40px;">
            <h3>Historique des Communications</h3>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Capteur</th>
                        <th>Données</th>
                    </tr>
                </thead>
                <tbody id="history-body">
                </tbody>
            </table>
        </div>
    </div>

    <script>
        async function refresh() {
            const resp = await fetch('/api/history');
            const data = await resp.json();
            
            const historyBody = document.getElementById('history-body');
            historyBody.innerHTML = '';
            
            if (data.length > 0) {
                // Update Live view with the latest
                const latest = data[0];
                document.getElementById('live-data').innerHTML = \`
                    <p><span class="status-dot"></span> <strong>\${latest.name}</strong></p>
                    <p>Température: <span class="value">\${latest.sensor_data.temperature || 'N/A'}°C</span></p>
                    <p>Humidité: <span class="value">\${latest.sensor_data.humidity || 'N/A'}%</span></p>
                    <p class="timestamp">Signal reçu à \${new Date(latest.timestamp).toLocaleString()}</p>
                \`;
            }

            data.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = \`
                    <td class="timestamp">\${new Date(row.timestamp).toLocaleString()}</td>
                    <td>\${row.name}</td>
                    <td>\${JSON.stringify(row.sensor_data)}</td>
                \`;
                historyBody.appendChild(tr);
            });
        }

        async function sendDownlink() {
            const devEui = document.getElementById('devEui').value;
            if(!devEui) return alert('Entrez un DevEUI');
            
            const resp = await fetch('/api/downlink', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ devEui, hexPayload: '0101' })
            });
            const result = await resp.json();
            if(result.success) alert('Downlink mis en file d\\'attente !');
            else alert('Erreur: ' + result.error);
        }

        setInterval(refresh, 5000);
        refresh();
    </script>
</body>
</html>
    `);
});

app.listen(port, () => {
    console.log(`Dashboard LoRa lancé sur http://localhost:${port}`);
});
