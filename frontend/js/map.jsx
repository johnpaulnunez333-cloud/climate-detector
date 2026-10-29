const { useState, useEffect, useRef } = React;

const PH_CENTER = [12.8797, 121.774];
const PH_BOUNDS = [[3.5, 115.5], [22.5, 128.5]];

function ClimateCard({ result, loading, error }) {
  if (loading) {
    return (
      <div className="result-card text-center py-5">
        <div className="spinner-border text-info" role="status"></div>
        <p className="mt-3 mb-0">Reading the sky over this spot...</p>
      </div>
    );
  }
  if (error) {
    return <div className="alert alert-danger mb-0">{error}</div>;
  }
  if (!result) {
    return (
      <div className="result-card">
        <h2 className="h5">Pick a spot</h2>
        <p className="mb-0 text-muted">Tap anywhere on the map or choose a city to detect its current climate.</p>
      </div>
    );
  }
  return (
    <div className={"result-card level-" + result.level}>
      <p className="place mb-1">{result.label}</p>
      <h2 className="climate-name">{result.climate}</h2>
      <p className="temp">{Math.round(result.temperature)}°C</p>
      <p className="advice">{result.advice}</p>
      <dl className="row stats mb-0">
        <dt className="col-7">Feels like</dt>
        <dd className="col-5">{Math.round(result.feels_like)}°C</dd>
        <dt className="col-7">Humidity</dt>
        <dd className="col-5">{result.humidity}%</dd>
        <dt className="col-7">Rain now</dt>
        <dd className="col-5">{result.rain} mm</dd>
        <dt className="col-7">Wind</dt>
        <dd className="col-5">{Math.round(result.wind)} km/h</dd>
      </dl>
    </div>
  );
}

function History({ items, onPick }) {
  if (!items.length) {
    return <p className="text-muted mb-0">Your recent checks will show up here.</p>;
  }
  return (
    <ul className="list-group list-group-flush history">
      {items.map((item) => (
        <li key={item.id} className="list-group-item">
          <button className="btn btn-link p-0 text-start" onClick={() => onPick(item)}>
            {item.label}
          </button>
          <span className="badge text-bg-light float-end">
            {item.climate} {item.temperature !== null ? Math.round(item.temperature) + "°C" : ""}
          </span>
        </li>
      ))}
    </ul>
  );
}

function App() {
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const [cities, setCities] = useState([]);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadHistory = () => {
    window.api("/api/history").then(setHistory).catch(() => {});
  };

  const detect = async (lat, lon, label) => {
    setLoading(true);
    setError("");
    if (mapRef.current) {
      if (markerRef.current) markerRef.current.remove();
      markerRef.current = L.marker([lat, lon]).addTo(mapRef.current);
      mapRef.current.flyTo([lat, lon], Math.max(mapRef.current.getZoom(), 8), { duration: 0.8 });
    }
    try {
      const query = "?lat=" + lat + "&lon=" + lon + (label ? "&label=" + encodeURIComponent(label) : "");
      const data = await window.api("/api/climate" + query);
      setResult(data);
      loadHistory();
    } catch (e) {
      setResult(null);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const map = L.map("map", {
      center: PH_CENTER,
      zoom: 6,
      minZoom: 5,
      maxBounds: PH_BOUNDS,
      maxBoundsViscosity: 1.0
    });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 18
    }).addTo(map);
    map.on("click", (e) => detect(e.latlng.lat, e.latlng.lng, ""));
    mapRef.current = map;
    window.api("/api/cities").then(setCities).catch(() => {});
    loadHistory();
    return () => map.remove();
  }, []);

  const onCity = (event) => {
    const city = cities.find((c) => c.name === event.target.value);
    if (city) detect(city.lat, city.lon, city.name);
  };

  return (
    <div className="row g-3">
      <div className="col-lg-8">
        <div id="map"></div>
      </div>
      <div className="col-lg-4">
        <label className="form-label fw-semibold" htmlFor="city">City</label>
        <select id="city" className="form-select mb-3" onChange={onCity} defaultValue="">
          <option value="" disabled>Choose a city</option>
          {cities.map((c) => (
            <option key={c.name} value={c.name}>{c.name}</option>
          ))}
        </select>
        <ClimateCard result={result} loading={loading} error={error} />
        <h3 className="h6 mt-4">Recent checks</h3>
        <History items={history} onPick={(item) => detect(item.lat, item.lon, item.label)} />
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
