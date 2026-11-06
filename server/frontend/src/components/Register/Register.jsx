import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Register({onAuth, request}) {
  const [error, setError] = useState('');
  const navigate = useNavigate();
  async function submit(event) {
    event.preventDefault();
    try {
      const result = await request('registration', Object.fromEntries(new FormData(event.currentTarget)));
      onAuth(result.userName);
      navigate('/');
    } catch (err) {
      setError(err.message);
    }
  }

  return <main><h1>Sign up</h1><form className="card form" onSubmit={submit}>
    <label>Username<input name="userName" autoComplete="username" maxLength="150" required /></label>
    <label>First Name<input name="firstName" autoComplete="given-name" maxLength="150" required /></label>
    <label>Last Name<input name="lastName" autoComplete="family-name" maxLength="150" required /></label>
    <label>Email<input name="email" type="email" autoComplete="email" required /></label>
    <label>Password<input name="password" type="password" autoComplete="new-password" minLength="8" required /></label>
    {error && <p role="alert">{error}</p>}<button type="submit">Register</button>
  </form></main>;
}
