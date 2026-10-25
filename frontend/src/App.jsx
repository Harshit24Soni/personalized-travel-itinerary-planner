import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";
import {
    ArrowRight,
    CalendarDays,
    Check,
    Compass,
    Download,
    MapPin,
    RefreshCw,
    Save,
    Sparkles,
    Users,
    Wallet,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
const supabase = supabaseUrl && supabaseAnonKey ? createClient(supabaseUrl, supabaseAnonKey) : null;
const slots = [
    "Morning Sightseeing",
    "Lunch Recommendation",
    "Afternoon Leisure",
    "Evening Dining & Entertainment",
];
const currencies = { EUR: 0.92, INR: 83, JPY: 150, THB: 36.5, AED: 3.67, GBP: 0.79, IDR: 15600, NPR: 134, TRY: 32, MXN: 17, USD: 1 };
const defaultStartDate = () => {
    const date = new Date();
    date.setDate(date.getDate() + 21);
    return date.toISOString().slice(0, 10);
};
const demoSessionId = () => {
    const storageKey = "wayfinder-demo-session";
    let value = window.localStorage.getItem(storageKey);
    if (!value) {
        value = window.crypto.randomUUID();
        window.localStorage.setItem(storageKey, value);
    }
    return value;
};

function formatCost(value, currency) {
    return `${currency} ${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function estimateUsd(value, currency) {
    return Number(value || 0) / (currencies[currency] || 1);
}

export default function App() {
    const [tab, setTab] = useState("discover");
    const [preferences, setPreferences] = useState({
        destination: "",
        vibe: "Beach",
        days: 4,
        start_date: defaultStartDate(),
        budget: "Moderate",
        party: "Solo",
        party_size: 1,
        pace: "Moderate",
        interests: ["Food", "History"],
        dietary_needs: [],
        provider: "Demo mode",
        api_key: "",
    });
    const [recommendations, setRecommendations] = useState([]);
    const [trip, setTrip] = useState(null);
    const [savedTrips, setSavedTrips] = useState([]);
    const [selectedDay, setSelectedDay] = useState(1);
    const [selectedSlot, setSelectedSlot] = useState(slots[0]);
    const [swapRequest, setSwapRequest] = useState("");
    const [session, setSession] = useState(null);
    const [authEmail, setAuthEmail] = useState("");
    const [authPassword, setAuthPassword] = useState("");
    const [notice, setNotice] = useState("");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);

    useEffect(() => {
        if (!supabase) return undefined;
        supabase.auth.getSession().then(({ data }) => setSession(data.session));
        const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => setSession(nextSession));
        return () => data.subscription.unsubscribe();
    }, []);

    useEffect(() => {
        loadTrips();
    }, [session]);

    async function api(path, options = {}) {
        const token = session?.access_token;
        const response = await fetch(`${API_BASE}${path}`, {
            ...options,
            headers: {
                "Content-Type": "application/json",
                "X-Session-ID": demoSessionId(),
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
                ...options.headers,
            },
        });
        const body = response.headers.get("content-type")?.includes("application/json")
            ? await response.json()
            : await response.blob();
        if (!response.ok) throw new Error(body.detail || "The request could not be completed.");
        return body;
    }

    async function loadTrips() {
        try {
            setSavedTrips(await api("/api/trips"));
        } catch {
            setSavedTrips([]);
        }
    }

    function updatePreference(name, value) {
        setPreferences((current) => ({ ...current, [name]: value }));
    }

    function toggleListPreference(name, value) {
        setPreferences((current) => {
            const selected = new Set(current[name]);
            selected.has(value) ? selected.delete(value) : selected.add(value);
            return { ...current, [name]: [...selected] };
        });
    }

    async function findDestinations(event) {
        event?.preventDefault();
        setBusy(true);
        setError("");
        try {
            const items = await api("/api/recommendations", {
                method: "POST",
                body: JSON.stringify({
                    vibe: preferences.vibe,
                    budget: preferences.budget,
                    month: Number(preferences.start_date.slice(5, 7)),
                    interests: preferences.interests,
                }),
            });
            setRecommendations(items);
        } catch (exception) {
            setError(exception.message);
        } finally {
            setBusy(false);
        }
    }

    async function generateTrip(event) {
        event?.preventDefault();
        setBusy(true);
        setError("");
        try {
            const result = await api("/api/itineraries", { method: "POST", body: JSON.stringify(preferences) });
            if (result.needs_destination) {
                setRecommendations(result.recommendations);
                setTab("discover");
                setNotice("Choose one of these destinations, then generate your trip.");
            } else {
                setTrip(result);
                setSelectedDay(1);
                setNotice("Itinerary created.");
                setTab("itinerary");
            }
        } catch (exception) {
            setError(exception.message);
        } finally {
            setBusy(false);
        }
    }

    async function saveTrip() {
        if (!trip) return;
        setBusy(true);
        setError("");
        try {
            const exists = savedTrips.some((saved) => saved.id === trip.id);
            const result = await api(exists ? `/api/trips/${encodeURIComponent(trip.id)}` : "/api/trips", {
                method: exists ? "PUT" : "POST",
                body: JSON.stringify({ trip }),
            });
            setNotice(result.storage === "supabase" ? "Trip saved to your account." : "Trip saved for this API session. Sign in and configure Supabase for durable account storage.");
            await loadTrips();
        } catch (exception) {
            setError(exception.message);
        } finally {
            setBusy(false);
        }
    }

    async function downloadPdf(selectedTrip = trip) {
        if (!selectedTrip) return;
        setBusy(true);
        setError("");
        try {
            const file = await api("/api/itineraries/pdf", { method: "POST", body: JSON.stringify({ trip: selectedTrip }) });
            const url = URL.createObjectURL(file);
            const link = document.createElement("a");
            link.href = url;
            link.download = `${selectedTrip.destination.toLowerCase().replaceAll(" ", "-")}-itinerary.pdf`;
            link.click();
            URL.revokeObjectURL(url);
        } catch (exception) {
            setError(exception.message);
        } finally {
            setBusy(false);
        }
    }

    async function applySwap(event) {
        event.preventDefault();
        if (!trip || !swapRequest.trim()) return;
        setBusy(true);
        setError("");
        try {
            const result = await api("/api/itineraries/swap", {
                method: "POST",
                body: JSON.stringify({ trip, day: selectedDay, slot: selectedSlot, request_text: swapRequest }),
            });
            setTrip(result);
            setSwapRequest("");
            setNotice("Only the selected activity was changed.");
        } catch (exception) {
            setError(exception.message);
        } finally {
            setBusy(false);
        }
    }

    async function regenerateDay() {
        if (!trip) return;
        setBusy(true);
        setError("");
        try {
            const result = await api("/api/itineraries/regenerate-day", {
                method: "POST",
                body: JSON.stringify({ trip, day: selectedDay }),
            });
            setTrip(result);
            setNotice(`Day ${selectedDay} regenerated; other days were preserved.`);
        } catch (exception) {
            setError(exception.message);
        } finally {
            setBusy(false);
        }
    }

    async function signIn(event, createAccount = false) {
        event.preventDefault();
        if (!supabase) {
            setError("Supabase sign-in is not configured. Demo mode remains available.");
            return;
        }
        const result = createAccount
            ? await supabase.auth.signUp({ email: authEmail, password: authPassword })
            : await supabase.auth.signInWithPassword({ email: authEmail, password: authPassword });
        if (result.error) setError(result.error.message);
        else setNotice(createAccount ? "Check your email to confirm your account." : "Signed in.");
    }

    async function signOut() {
        await supabase?.auth.signOut();
        setSession(null);
        setNotice("Signed out.");
    }

    const totalUsd = trip?.itinerary?.reduce(
        (sum, day) => sum + day.activities.reduce((daySum, item) => daySum + estimateUsd(item.cost_local, item.currency), 0),
        0,
    ) || 0;
    const currentDay = trip?.itinerary?.find((day) => day.day === selectedDay);

    return (
        <div className="app-shell">
            <header className="topbar">
                <a className="wordmark" href="#top"><span className="wordmark-mark"><Compass size={19} /></span> wayfinder<span className="wordmark-dot">.</span></a>
                <div className="topbar-right">
                    {supabase && session ? (
                        <button className="text-button" onClick={signOut}>Sign out</button>
                    ) : null}
                    <span className="session-status">{session ? "Account synced" : "Demo session"}</span>
                </div>
            </header>

            <main id="top" className="page-wrap">
                <section className="hero-row">
                    <div>
                        <p className="eyebrow">PERSONALIZED TRAVEL ITINERARY PLANNER</p>
                        <h1>Go somewhere<br /><em>worth remembering.</em></h1>
                        <p className="hero-copy">A thoughtful route, built around your pace, budget, and the things you love.</p>
                    </div>
                    <div className="hero-stamp"><Compass size={19} /><span>Made for<br />the way you travel</span></div>
                </section>

                <section className="planner-layout">
                    <aside className="preference-panel">
                        <div className="panel-heading"><div><span className="section-index">01</span><h2>Your trip</h2></div><span className="tiny-label">PLAN</span></div>
                        <form className="preferences-form" onSubmit={generateTrip}>
                            <label>Destination <span className="optional">optional</span>
                                <input value={preferences.destination} onChange={(event) => updatePreference("destination", event.target.value)} placeholder="Choose a place or find inspiration" />
                            </label>
                            <label>Travel mood
                                <select value={preferences.vibe} onChange={(event) => updatePreference("vibe", event.target.value)}>
                                    {["Beach", "Mountains", "Cultural", "Urban", "Food-focused", "Adventure", "Relaxed"].map((option) => <option key={option}>{option}</option>)}
                                </select>
                            </label>
                            <div className="field-grid">
                                <label>Days<input type="number" min="1" max="14" value={preferences.days} onChange={(event) => updatePreference("days", Number(event.target.value))} /></label>
                                <label>Travelers<input type="number" min="1" max="20" value={preferences.party_size} onChange={(event) => updatePreference("party_size", Number(event.target.value))} /></label>
                            </div>
                            <label>Start date<input type="date" value={preferences.start_date} onChange={(event) => updatePreference("start_date", event.target.value)} /></label>
                            <div className="field-grid">
                                <label>Budget<select value={preferences.budget} onChange={(event) => updatePreference("budget", event.target.value)}>{["Budget", "Moderate", "Luxury"].map((option) => <option key={option}>{option}</option>)}</select></label>
                                <label>Travel party<select value={preferences.party} onChange={(event) => updatePreference("party", event.target.value)}>{["Solo", "Couple", "Family", "Friends"].map((option) => <option key={option}>{option}</option>)}</select></label>
                            </div>
                            <label>Pace<select value={preferences.pace} onChange={(event) => updatePreference("pace", event.target.value)}>{["Relaxed", "Moderate", "Fast-Paced"].map((option) => <option key={option}>{option}</option>)}</select></label>
                            <fieldset><legend>Interests</legend><div className="check-grid">{["Food", "Adventure", "History", "Nightlife"].map((item) => <label className="check-option" key={item}><input type="checkbox" checked={preferences.interests.includes(item)} onChange={() => toggleListPreference("interests", item)} />{item}</label>)}</div></fieldset>
                            <fieldset><legend>Dietary needs</legend><div className="check-grid">{["Vegetarian", "Vegan", "Gluten-free", "Halal", "Dairy-free"].map((item) => <label className="check-option" key={item}><input type="checkbox" checked={preferences.dietary_needs.includes(item)} onChange={() => toggleListPreference("dietary_needs", item)} />{item}</label>)}</div></fieldset>
                            <label>Generation mode<select value={preferences.provider} onChange={(event) => updatePreference("provider", event.target.value)}>{["Demo mode", "Gemini", "Groq"].map((option) => <option key={option}>{option}</option>)}</select></label>
                            {preferences.provider !== "Demo mode" ? <label>API key<input type="password" autoComplete="off" value={preferences.api_key} onChange={(event) => updatePreference("api_key", event.target.value)} placeholder="Used for this request only" /></label> : null}
                            <button className="primary-button full-button" disabled={busy} type="submit"><Sparkles size={16} />{busy ? "Working..." : "Build my itinerary"}</button>
                        </form>
                        {supabase ? (
                            <form className="auth-box" onSubmit={(event) => signIn(event)}>
                                <div className="auth-title">Save trips to your account</div>
                                <input aria-label="Account email" type="email" value={authEmail} onChange={(event) => setAuthEmail(event.target.value)} placeholder="Email" />
                                <input aria-label="Account password" type="password" autoComplete="current-password" value={authPassword} onChange={(event) => setAuthPassword(event.target.value)} placeholder="Password" />
                                <div className="auth-actions"><button className="text-button" type="submit">Sign in</button><button className="text-button" type="button" onClick={(event) => signIn(event, true)}>Create account</button></div>
                            </form>
                        ) : <p className="subtle-note">Account persistence is optional. Demo mode works without a Supabase project.</p>}
                    </aside>

                    <section className="content-panel">
                        <div className="tabbar" role="tablist" aria-label="Trip planner views">
                            {[["discover", "Discover"], ["itinerary", "Itinerary"], ["customize", "Customize"], ["library", "Trip library"]].map(([key, label], index) => <button key={key} role="tab" aria-selected={tab === key} className={tab === key ? "tab active" : "tab"} onClick={() => setTab(key)}><span>0{index + 1}</span>{label}</button>)}
                        </div>
                        {error ? <div className="alert alert-error" role="alert">{error}</div> : null}
                        {notice ? <div className="alert alert-success" role="status"><Check size={15} />{notice}</div> : null}

                        {tab === "discover" ? <section className="view-section">
                            <div className="view-heading"><div><span className="section-index">01 / DISCOVER</span><h2>Find your kind of place</h2></div><button className="secondary-button" onClick={findDestinations} disabled={busy}><Compass size={15} />Find destinations</button></div>
                            <p className="section-copy">Recommendations consider your mood, budget, travel season, and interests.</p>
                            <div className="recommendation-grid">{recommendations.map((item) => <article className="destination-card" key={item.city}>
                                <div className={`destination-cover cover-${item.city.toLowerCase().replaceAll(" ", "-")}`}><MapPin size={17} /><span>{item.country}</span></div>
                                <div className="destination-body"><div className="destination-line"><h3>{item.city}</h3><span className="score">{item.score} fit</span></div><p>{item.reason}</p><div className="tag-row">{item.tags.map((tag) => <span className="tag" key={tag}>{tag}</span>)}</div><button className="text-button" onClick={() => { updatePreference("destination", item.city); setTab("itinerary"); }}>Choose destination <ArrowRight size={14} /></button></div>
                            </article>)}</div>
                            <p className="disclaimer">Season fit is a month-based guide, not a live forecast. Prices are estimates.</p>
                        </section> : null}

                        {tab === "itinerary" ? <section className="view-section">
                            <div className="view-heading"><div><span className="section-index">02 / ITINERARY</span><h2>{trip ? `${trip.destination}, ${trip.country}` : "Day by day, made lighter"}</h2></div>{trip ? <div className="heading-actions"><button className="icon-button" title="Save trip" aria-label="Save trip" onClick={saveTrip}><Save size={17} /></button><button className="icon-button" title="Download PDF" aria-label="Download PDF" onClick={() => downloadPdf()}><Download size={17} /></button></div> : null}</div>
                            {trip ? <><div className="trip-summary"><span><CalendarDays size={15} />{trip.start_date} to {trip.end_date}</span><span><Users size={15} />{trip.party_size || trip.party}</span><span><Wallet size={15} />${totalUsd.toFixed(2)} estimated</span></div>
                                {trip.itinerary.map((day) => <article className="day-block" key={day.day}><div className="day-title"><span>DAY {String(day.day).padStart(2, "0")}</span><h3>{day.title}</h3></div>{day.activities.map((activity) => <div className="activity-row" key={activity.slot}><div><span className="activity-slot">{activity.slot}</span><h4>{activity.name}</h4><p>{activity.area} · {activity.description}</p></div><div className="activity-cost">{formatCost(activity.cost_local, activity.currency)}<small>${estimateUsd(activity.cost_local, activity.currency).toFixed(2)} USD</small></div></div>)}</article>)}
                                <p className="disclaimer">Estimates exclude lodging, transit, taxes, and live price changes.</p>
                            </> : <div className="empty-state"><Compass size={30} /><h3>Your itinerary will appear here</h3><p>Choose a destination or build one from your travel preferences.</p><button className="primary-button" onClick={() => setTab("discover")}>Explore destinations <ArrowRight size={15} /></button></div>}
                        </section> : null}

                        {tab === "customize" ? <section className="view-section">
                            <div className="view-heading"><div><span className="section-index">03 / CUSTOMIZE</span><h2>Shape the details</h2></div></div>
                            {!trip ? <div className="empty-state compact"><h3>Start with an itinerary</h3><p>Your changes will only affect one selected day or time slot.</p><button className="text-button" onClick={() => setTab("itinerary")}>Open itinerary <ArrowRight size={14} /></button></div> : <><div className="custom-controls"><label>Day<select value={selectedDay} onChange={(event) => setSelectedDay(Number(event.target.value))}>{trip.itinerary.map((day) => <option key={day.day} value={day.day}>Day {day.day}</option>)}</select></label><label>Time slot<select value={selectedSlot} onChange={(event) => setSelectedSlot(event.target.value)}>{slots.map((slot) => <option key={slot}>{slot}</option>)}</select></label></div><p className="current-activity">Current: {currentDay?.activities.find((item) => item.slot === selectedSlot)?.name}</p><form className="swap-form" onSubmit={applySwap}><label>What would you like instead?<input value={swapRequest} onChange={(event) => setSwapRequest(event.target.value)} placeholder="Try: vegetarian lunch, outdoor market, or history museum" /></label><button className="primary-button" disabled={busy || !swapRequest.trim()} type="submit"><RefreshCw size={15} />Apply swap</button></form><button className="secondary-button" disabled={busy} onClick={regenerateDay}><RefreshCw size={15} />Regenerate this day only</button></>}
                        </section> : null}

                        {tab === "library" ? <section className="view-section">
                            <div className="view-heading"><div><span className="section-index">04 / TRIP LIBRARY</span><h2>Saved journeys</h2></div></div>
                            <p className="section-copy">{session ? "Trips are saved to your Supabase account." : "Sign in and configure Supabase for durable account storage; demo trips last for the current API process."}</p>
                            {savedTrips.length ? <div className="library-list">{savedTrips.map((item) => <article className="library-row" key={item.id}><div><h3>{item.destination}, {item.country}</h3><p>{item.start_date} · {item.days} days · {item.source}</p></div><div className="library-actions"><button className="text-button" onClick={() => { setTrip(item); setTab("itinerary"); }}>Open</button><button className="icon-button" title="Download PDF" aria-label="Download PDF" onClick={() => downloadPdf(item)}><Download size={16} /></button></div></article>)}</div> : <div className="empty-state compact"><h3>No saved trips yet</h3><p>Save an itinerary to keep it in your library.</p></div>}
                        </section> : null}
                    </section>
                </section>
                <footer className="page-footer"><span>Wayfinder · Travel, thoughtfully planned.</span><span>Currency estimates are indicative.</span></footer>
            </main>
        </div>
    );
}
