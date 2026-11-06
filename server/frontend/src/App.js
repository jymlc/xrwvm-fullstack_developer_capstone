import { useEffect, useState } from 'react';
import { Link, Route, Routes, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import Register from './components/Register/Register';

export async function api(path, data) {
  const csrf = document.cookie.split('; ').find(item => item.startsWith('csrftoken='))?.slice(10) || '';
  const response = await fetch('/djangoapp/' + path, data === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
    body: JSON.stringify(data),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed.');
  return result;
}

function useResource(path) {
  const [result, setResult] = useState({});
  useEffect(() => {
    let active = true;
    setResult({});
    api(path).then(data => { if (active) setResult(data); })
      .catch(error => { if (active) setResult({error: error.message}); });
    return () => { active = false; };
  }, [path]);
  return result;
}

function Dealers({user}) {
  const [query, setQuery] = useSearchParams();
  const state = query.get('state') || '';
  const all = useResource('get_dealers');
  const filtered = useResource('get_dealers' + (state ? '/' + encodeURIComponent(state) : ''));
  const rows = state ? filtered.dealers : all.dealers;
  const states = [...new Set((all.dealers || []).map(row => row.state))].sort();
  return <main>
    <p className="eyebrow">National branch directory</p><h1>Find a dealership</h1>
    <p>Browse branches and read reviews from other drivers.</p>
    <label htmlFor="state">Filter by state</label>
    <select id="state" value={state} onChange={e => setQuery(e.target.value ? {state: e.target.value} : {})}>
      <option value="">All states</option>
      {states.map(name => <option key={name}>{name}</option>)}
    </select>
    <p role="status">{filtered.error || all.error || (rows ? rows.length + ' dealerships' : 'Loading dealerships…')}</p>
    <div className="table-wrap"><table><thead><tr><th>Dealership</th><th>City</th><th>State</th><th>Address</th>{user && <th>Review</th>}</tr></thead>
    <tbody>{(rows || []).map(row => <tr key={row.id}><td><Link to={'/dealer/' + row.id}>{row.full_name}</Link></td>
      <td>{row.city}</td><td>{row.state}</td><td>{row.address}</td>
      {user && <td><Link to={'/dealer/' + row.id + '/review'}>Review Dealer</Link></td>}</tr>)}</tbody></table></div>
  </main>;
}

function Dealer({user}) {
  const {id} = useParams();
  const {dealer, error} = useResource('get_dealer_details/' + id);
  const reviews = useResource('get_dealer_reviews/' + id);
  return <main><Link to="/">← All dealerships</Link><h1>{dealer?.full_name || 'Dealer details'}</h1>
    {dealer && <p>{dealer.address}, {dealer.city}, {dealer.state} {dealer.zip}</p>}
    {error && <p role="alert">{error}</p>}
    {user && dealer && <Link className="button" to={'/dealer/' + id + '/review'}>Review Dealer</Link>}
    <h2>Customer reviews</h2>
    {reviews.error && <p role="alert">{reviews.error}</p>}
    {reviews.reviews?.length === 0 && <p>No reviews yet.</p>}
    {reviews.reviews?.map((row, index) => <article className="card" key={row.id || index}>
      <h3>{row.name}</h3><p>{row.review}</p>
      <p className="muted">{row.car_year} {row.car_make} {row.car_model}{row.sentiment ? ' · ' + row.sentiment : ''}</p>
    </article>)}
  </main>;
}

function Review({user}) {
  const {id} = useParams();
  const navigate = useNavigate();
  const {dealer} = useResource('get_dealer_details/' + id);
  const {CarMakes} = useResource('get_cars');
  const [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api('add_review', {dealership: Number(id), review: form.get('review'),
        modelId: Number(form.get('model')), purchase: form.has('purchase'), purchaseDate: form.get('purchaseDate')});
      navigate('/dealer/' + id);
    } catch (err) { setError(err.message); }
  }
  if (!user) return <main><h1>Post Review</h1><Link to="/login">Log in to post a review</Link></main>;
  return <main><h1>Post Review</h1><p>{dealer?.full_name}</p><form className="card form" onSubmit={submit}>
    <label>Review<textarea name="review" rows="5" maxLength="2000" required /></label>
    <label>Car make and model<select name="model" required defaultValue=""><option value="" disabled>Select a model</option>
      {CarMakes?.map(make => <optgroup key={make.id} label={make.name}>{make.models.map(model =>
        <option key={model.id} value={model.id}>{make.name} {model.name} ({model.year})</option>)}</optgroup>)}</select></label>
    <label className="inline"><input type="checkbox" name="purchase" /> I bought a car here</label>
    <label>Purchase date<input name="purchaseDate" type="date" /></label>
    {error && <p role="alert">{error}</p>}<button>Submit review</button>
  </form></main>;
}

function Login({onAuth}) {
  const navigate = useNavigate();
  const [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try { const result = await api('login', data); onAuth(result.userName); navigate('/'); }
    catch (err) { setError(err.message); }
  }
  return <main><h1>Log in</h1><form className="card form" onSubmit={submit}>
    <label>Username<input name="userName" autoComplete="username" required /></label>
    <label>Password<input name="password" type="password" autoComplete="current-password" required /></label>
    {error && <p role="alert">{error}</p>}<button>Log in</button></form></main>;
}

export default function App() {
  const [user, setUser] = useState('');
  const [authError, setAuthError] = useState('');
  const navigate = useNavigate();
  useEffect(() => { api('session').then(result => setUser(result.userName)).catch(() => {}); }, []);
  async function signOut() {
    try { await api('logout', {}); setUser(''); navigate('/'); }
    catch (error) { setAuthError(error.message); }
  }
  return <><link rel="stylesheet" href="/static/dealership.css" />
    <header><nav aria-label="Main navigation">
      <Link className="brand" to="/">Cars Dealership</Link><Link to="/">Dealers</Link>
      <a href="/about">About Us</a><a href="/contact">Contact Us</a>
      {user ? <><span className="user">Signed in as <strong>{user}</strong></span><button onClick={signOut}>Log out</button></>
        : <><Link className="user" to="/login">Log in</Link><Link to="/register">Sign up</Link></>}
    </nav></header>{authError && <p role="alert">{authError}</p>}
    <Routes><Route path="/" element={<Dealers user={user} />} /><Route path="/dealers" element={<Dealers user={user} />} />
      <Route path="/login" element={<Login onAuth={setUser} />} /><Route path="/register" element={<Register onAuth={setUser} request={api} />} />
      <Route path="/dealer/:id" element={<Dealer user={user} />} /><Route path="/dealer/:id/review" element={<Review user={user} />} /></Routes></>;
}
