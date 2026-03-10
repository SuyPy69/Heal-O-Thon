from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

# --- CONFIGURATION ---
DB_PATH = r'C:\Users\rishi\PycharmProjects\Healo\hospitals.db'


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS hospitals
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       name
                       TEXT
                       NOT
                       NULL,
                       location
                       TEXT
                       NOT
                       NULL
                   )
                   ''')

    # Safely update existing databases to include 'pincode' without losing data
    cursor.execute("PRAGMA table_info(hospitals)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'pincode' not in columns:
        cursor.execute("ALTER TABLE hospitals ADD COLUMN pincode TEXT DEFAULT 'Unknown'")

    conn.commit()
    conn.close()


def get_chrome_path():
    try:
        path = uc.find_chrome_executable()
        if path: return path
    except:
        pass

    possible_paths = [
        os.path.expanduser(r"~\AppData\Local\Google\Chrome SxS\Application\chrome.exe"),  # Canary
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
    ]
    for p in possible_paths:
        if os.path.exists(p): return p
    return None


# --- THE VISIBLE GOOGLE MAPS SCRAPER ---
@app.route('/scrape_traffic', methods=['POST'])
def scrape_traffic():
    data = request.json
    start_lat, start_lng = data['start']
    end_lat, end_lng = data['end']

    google_url = f"https://www.google.com/maps/dir/{start_lat},{start_lng}/{end_lat},{end_lng}/"

    driver = None
    try:
        options = uc.ChromeOptions()
        chrome_bin = get_chrome_path()
        if chrome_bin: options.binary_location = chrome_bin

        driver = uc.Chrome(options=options, use_subprocess=True)
        driver.get(google_url)

        wait = WebDriverWait(driver, 15)
        time_element = wait.until(EC.presence_of_element_located(
            (By.XPATH, "(//div[contains(text(), ' min') or contains(text(), ' hr')])[1]")))
        distance_element = driver.find_element(By.XPATH, "(//div[contains(text(), ' km')])[1]")

        travel_time = time_element.text
        travel_dist = distance_element.text

        driver.quit()

        return jsonify({"status": "success", "time": travel_time, "distance": travel_dist, "url": google_url})
    except Exception as e:
        if driver:
            try:
                driver.quit()
            except:
                pass
        print(f"Scrape Error: {e}")
        return jsonify({"status": "error", "message": "Scrape Timeout/Failed"}), 500


# --- DATABASE ROUTES ---
@app.route('/get_saved_hospitals')
def get_saved_hospitals():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, location, pincode FROM hospitals')
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "name": r[1], "location": r[2], "pincode": r[3]} for r in rows])


@app.route('/save_hospital_sql', methods=['POST'])
def save_hospital_sql():
    hospitals = request.json['hospitals']
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for h in hospitals:
            cursor.execute('INSERT INTO hospitals (name, location, pincode) VALUES (?, ?, ?)',
                           (h['name'], h['location'], h['pincode']))
        conn.commit()
        conn.close()
        return jsonify(
            {"status": "success", "message": f"Successfully appended {len(hospitals)} hospitals to Database!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/delete_hospital_sql', methods=['POST'])
def delete_hospital_sql():
    hosp_id = request.json['id']
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM hospitals WHERE id = ?', (hosp_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Deleted from database."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/delete_hospital_mass', methods=['POST'])
def delete_hospital_mass():
    ids = request.json['ids']
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Delete multiple IDs at once
        cursor.executemany('DELETE FROM hospitals WHERE id = ?', [(i,) for i in ids])
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": f"Mass deleted {len(ids)} hospitals."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/')
def index():
    init_db()
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Healo | Bengaluru</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <link rel="stylesheet" href="https://unpkg.com/leaflet-routing-machine/dist/leaflet-routing-machine.css" />
        <style>
            body { margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; }
            #map { position: absolute; top: 0; bottom: 0; width: 100%; z-index: 1; cursor: grab; }

            #sidebar {
                position: fixed; left: 15px; top: 15px; bottom: 100px; width: 320px;
                background: white; z-index: 1000; border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2); padding: 20px; overflow-y: auto;
            }
            #trip-card {
                position: fixed; top: 15px; right: 15px; z-index: 1000;
                background: #1e293b; color: white; padding: 15px 25px;
                border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.4);
                border-left: 6px solid #fbbf24; cursor: move; display: none; transition: 0.3s; min-width: 180px;
            }
            .hospital-item { display: flex; justify-content: space-between; background: #eef2ff; padding: 10px; margin-bottom: 8px; border-radius: 8px; font-size: 13px; }
            .save-btn { position: fixed; bottom: 25px; right: 25px; z-index: 1000; padding: 15px 35px; background: #4f46e5; color: white; border: none; border-radius: 50px; cursor: pointer; font-weight: bold; }

            .btn-group { display: flex; gap: 10px; margin-bottom: 15px; }
            .mass-add-btn { background: #10b981; color: white; width: 50%; padding: 10px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; transition: 0.2s; font-size: 12px;}
            .mass-add-btn.active { background: #059669; box-shadow: inset 0 3px 6px rgba(0,0,0,0.2); }

            .mass-del-btn { background: #ef4444; color: white; width: 50%; padding: 10px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; transition: 0.2s; font-size: 12px;}
            .mass-del-btn.active { background: #b91c1c; box-shadow: inset 0 3px 6px rgba(0,0,0,0.2); }

            .instructions { font-size: 11px; color: #64748b; margin-bottom: 15px; background: #f8fafc; padding: 10px; border-radius: 6px; }
            .tick-icon { font-size: 24px; color: #10b981; text-align: center; }
            .cross-icon { font-size: 24px; color: #ef4444; cursor: pointer; text-align: center; }

            .loader { border: 3px solid #334155; border-top: 3px solid #fbbf24; border-radius: 50%; width: 14px; height: 14px; animation: spin 1s linear infinite; display: inline-block; margin-right: 5px; vertical-align: middle; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

            #openMapsBtn { background: #ea4335; color: white; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: bold; width: 100%; display: none; margin-top: 5px; text-transform: uppercase; }
        </style>
    </head>
    <body>

    <div id="sidebar">
        <h2 style="margin:0 0 10px 0;">🏥 Healo Queue</h2>
        <div class="instructions">
            <b>Shift + Left Click:</b> Start Point<br>
            <b>Shift + Right Click:</b> Destination
        </div>

        <div class="btn-group">
            <button id="massAddBtn" class="mass-add-btn">🟩 Mass Add</button>
            <button id="massDelBtn" class="mass-del-btn">🟥 Mass Delete</button>
        </div>

        <div id="hospital-list"></div>
    </div>

    <div id="trip-card" draggable="true">
        <div style="font-size: 10px; color: #94a3b8; text-transform: uppercase;">Google Live Traffic 📡</div>
        <div id="trip-stats" style="font-size: 18px; font-weight: bold; color: #fbbf24; margin: 5px 0;"></div>
        <button id="openMapsBtn">🚀 Open in Maps</button>
    </div>

    <button id="saveBtn" class="save-btn" onclick="syncDB()">💾 SYNC DATABASE</button>
    <div id="map"></div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet-routing-machine/dist/leaflet-routing-machine.js"></script>

    <script>
        var map = L.map('map', {zoomControl: false}).setView([12.9716, 77.5946], 12);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

        var routingControl = L.Routing.control({
            waypoints: [], routeWhileDragging: false, show: false,
            router: L.Routing.osrmv1({ serviceUrl: 'https://router.project-osrm.org/route/v1' })
        }).addTo(map);

        var startM = null, endM = null;
        var queue = [];

        // Tracking Memory
        var savedLocs = new Set();
        var mapHospitals = []; // Unsaved markers {name, lat, lon, id, pincode}
        var savedDataMap = {}; // Saved markers {db_id, marker_obj} keyed by location string

        var googleUrlToOpen = "";

        // --- SHIFT + CLICK ROUTING ---
        map.on('click', function(e) {
            if (e.originalEvent.shiftKey) {
                if (startM) map.removeLayer(startM);
                startM = L.marker(e.latlng).addTo(map).bindPopup("Start");
                triggerScraper();
            }
        });

        map.on('contextmenu', function(e) {
            e.originalEvent.preventDefault();
            if (e.originalEvent.shiftKey) {
                if (endM) map.removeLayer(endM);
                endM = L.marker(e.latlng).addTo(map).bindPopup("Destination");
                triggerScraper();
            }
        });

        function triggerScraper() {
            if (startM && endM) {
                routingControl.setWaypoints([startM.getLatLng(), endM.getLatLng()]);

                var card = document.getElementById('trip-card');
                var btn = document.getElementById('openMapsBtn');

                card.style.display = 'block';
                btn.style.display = 'none'; 
                document.getElementById('trip-stats').innerHTML = '<div class="loader"></div> Scraping Google...';

                fetch('/scrape_traffic', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ start: [startM.getLatLng().lat, startM.getLatLng().lng], end: [endM.getLatLng().lat, endM.getLatLng().lng] })
                }).then(r => r.json()).then(data => {
                    if (data.status === 'success') {
                        document.getElementById('trip-stats').innerHTML = data.time + " | " + data.distance;
                        googleUrlToOpen = data.url;
                        btn.style.display = 'block'; 
                    } else {
                        document.getElementById('trip-stats').innerHTML = "⚠️ " + data.message;
                    }
                }).catch(err => { document.getElementById('trip-stats').innerHTML = "⚠️ Scrape Failed"; });
            }
        }

        document.getElementById('openMapsBtn').onclick = function(e) {
            e.stopPropagation(); 
            if (googleUrlToOpen) { window.open(googleUrlToOpen, '_blank'); }
        };

        // --- MASS SELECTION MODES ---
        var selectMode = 'none'; // 'add' or 'del'
        var rectBox = null, startPoint = null;

        var btnAdd = document.getElementById('massAddBtn');
        var btnDel = document.getElementById('massDelBtn');

        function updateMode(newMode) {
            selectMode = (selectMode === newMode) ? 'none' : newMode;

            btnAdd.classList.remove('active');
            btnDel.classList.remove('active');

            if (selectMode === 'none') {
                map.dragging.enable(); 
                document.getElementById('map').style.cursor = 'grab';
            } else {
                map.dragging.disable(); 
                document.getElementById('map').style.cursor = 'crosshair';
                if (selectMode === 'add') btnAdd.classList.add('active');
                if (selectMode === 'del') btnDel.classList.add('active');
            }
        }

        btnAdd.onclick = () => updateMode('add');
        btnDel.onclick = () => updateMode('del');

        map.on('mousedown', function(e) {
            if (selectMode === 'none' || e.originalEvent.button !== 0 || e.originalEvent.shiftKey) return;
            startPoint = e.latlng;
            var boxColor = selectMode === 'add' ? '#10b981' : '#ef4444';
            rectBox = L.rectangle([startPoint, startPoint], {color: boxColor, weight: 2, fillOpacity: 0.2}).addTo(map);
        });

        map.on('mousemove', function(e) {
            if (selectMode !== 'none' && rectBox && startPoint) {
                rectBox.setBounds([startPoint, e.latlng]);
            }
        });

        map.on('mouseup', function(e) {
            if (selectMode !== 'none' && rectBox && startPoint) {
                var bounds = L.latLngBounds(startPoint, e.latlng);
                map.removeLayer(rectBox);
                rectBox = null; startPoint = null;

                if (selectMode === 'add') {
                    // Mass ADD
                    var addedCount = 0;
                    mapHospitals.forEach(h => {
                        var point = L.latLng(h.lat, h.lon);
                        if (bounds.contains(point)) {
                            if (!queue.some(q => q.location === h.id) && !savedLocs.has(h.id)) {
                                addToQueue(h.name, h.lat, h.lon, h.pincode);
                                addedCount++;
                            }
                        }
                    });
                    if(addedCount > 0) alert("Mass selected " + addedCount + " hospitals!");

                } else if (selectMode === 'del') {
                    // Mass DELETE
                    var idsToDelete = [];
                    var locsToDelete = [];

                    for (var loc in savedDataMap) {
                        var coords = loc.split(',').map(Number);
                        var point = L.latLng(coords[0], coords[1]);
                        if (bounds.contains(point)) {
                            idsToDelete.push(savedDataMap[loc].db_id);
                            locsToDelete.push(loc);
                        }
                    }

                    if (idsToDelete.length > 0) {
                        if (confirm(`Are you sure you want to MASS DELETE ${idsToDelete.length} hospitals from the database?`)) {
                            fetch('/delete_hospital_mass', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ ids: idsToDelete })
                            }).then(r => r.json()).then(d => {
                                if (d.status === 'success') {
                                    // Remove markers & update memory
                                    locsToDelete.forEach(loc => {
                                        map.removeLayer(savedDataMap[loc].marker);
                                        delete savedDataMap[loc];
                                        savedLocs.delete(loc);
                                    });
                                    alert(d.message);
                                    fetchHospitals(); // Refresh red crosses
                                }
                            });
                        }
                    } else {
                        alert("No saved hospitals found in that area.");
                    }
                }

                // Reset mode after selection
                updateMode('none');
            }
        });

        // --- HOSPITAL SCOUTING (OSM) ---
        map.on('moveend', fetchHospitals);
        function fetchHospitals() {
            var b = map.getBounds();
            var q = `[out:json];node["amenity"="hospital"](${b.getSouth()},${b.getWest()},${b.getNorth()},${b.getEast()});out;`;
            fetch("https://overpass-api.de/api/interpreter?data=" + encodeURIComponent(q))
            .then(r => r.json()).then(data => {
                data.elements.forEach(el => {
                    var loc = el.lat.toFixed(6) + ", " + el.lon.toFixed(6);
                    if (savedLocs.has(loc)) return; 

                    if (!mapHospitals.some(h => h.id === loc)) {
                        var pincode = el.tags['addr:postcode'] || "Unknown";
                        var name = el.tags.name || "Hospital";

                        var m = L.marker([el.lat, el.lon], { icon: L.divIcon({ className: 'cross-icon', html: '✚', iconSize: [25, 25] }) }).addTo(map);
                        m.bindPopup(`<b>${name}</b><br>Pin: ${pincode}<br><button onclick="addToQueue('${name}', ${el.lat}, ${el.lon}, '${pincode}')" style="width:100%; cursor:pointer; background:#10b981; color:white; border:none; padding:5px; border-radius:5px; margin-top:5px;">Add to Queue</button>`);

                        mapHospitals.push({ name: name, lat: el.lat, lon: el.lon, id: loc, pincode: pincode });
                    }
                });
            });
        }

        // --- QUEUE & DATABASE LOGIC ---
        window.addToQueue = function(name, lat, lon, pincode) {
            queue.push({ id: Date.now() + Math.random(), name: name, location: lat.toFixed(6) + ", " + lon.toFixed(6), pincode: pincode });
            renderQueue();
        }

        function renderQueue() {
            var list = document.getElementById('hospital-list'); list.innerHTML = "";
            queue.forEach(h => { 
                list.innerHTML += `<div class="hospital-item"><span>${h.name} <small style="color:#64748b">(${h.pincode})</small></span><span style="color:red; cursor:pointer" onclick="removeQ(${h.id})">✖</span></div>`; 
            });
        }

        window.removeQ = function(id) { queue = queue.filter(h => h.id !== id); renderQueue(); };

        window.syncDB = function() {
            if (queue.length === 0) return alert("Queue is empty!");
            fetch('/save_hospital_sql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ hospitals: queue }) })
            .then(r => r.json()).then(d => { alert(d.message); queue = []; renderQueue(); loadSaved(); });
        }

        function loadSaved() {
            fetch('/get_saved_hospitals').then(r => r.json()).then(data => {
                data.forEach(h => {
                    if (!savedLocs.has(h.location)) {
                        var c = h.location.split(',').map(Number);
                        var m = L.marker(c, { icon: L.divIcon({ className: 'tick-icon', html: '✔️', iconSize: [30, 30] }) }).addTo(map);

                        m.bindPopup(`<b>${h.name}</b><br>Pin: ${h.pincode}<br><button onclick="deleteFromDB(${h.id}, '${h.location}')" style="width:100%; cursor:pointer; background:#ef4444; color:white; border:none; padding:5px; border-radius:5px; margin-top:5px;">Delete from DB</button>`);

                        savedLocs.add(h.location);
                        savedDataMap[h.location] = { db_id: h.id, marker: m }; 
                    }
                });
            });
        }

        window.deleteFromDB = function(db_id, loc_string) {
            if(!confirm("Remove this hospital from the database?")) return;
            fetch('/delete_hospital_sql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: db_id }) })
            .then(r => r.json()).then(data => {
                if (data.status === 'success') {
                    if (savedDataMap[loc_string]) {
                        map.removeLayer(savedDataMap[loc_string].marker);
                        delete savedDataMap[loc_string];
                    }
                    savedLocs.delete(loc_string);
                    fetchHospitals();
                } else { alert("Failed to delete: " + data.message); }
            });
        }

        loadSaved(); fetchHospitals();

        // Draggable Widget Logic
        var card = document.getElementById("trip-card");
        var active = false, currentX, currentY, initialX, initialY, xOffset = 0, yOffset = 0;
        card.addEventListener("mousedown", (e) => { 
            if(e.target.id === 'openMapsBtn') return; 
            initialX = e.clientX - xOffset; initialY = e.clientY - yOffset; 
            if (e.target === card || card.contains(e.target)) active = true; 
        });
        document.addEventListener("mouseup", () => active = false);
        document.addEventListener("mousemove", (e) => { 
            if (active) { 
                currentX = e.clientX - initialX; currentY = e.clientY - initialY; 
                xOffset = currentX; yOffset = currentY; 
                card.style.transform = `translate(${currentX}px, ${currentY}px)`; 
            } 
        });
    </script>
    </body>
    </html>
    """
    return render_template_string(html_template)


if __name__ == '__main__':
    app.run(debug=True)

