import { Routes, Route, Navigate } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { InsightsPage } from './pages/InsightsPage';
import { LoginPage } from './pages/LoginPage';
import { useEffect, useState } from 'react';
import { isAuthenticated } from './services/auth';

function App() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const auth = await isAuthenticated();
    setAuthenticated(auth);
  };

  // Show loading state while checking authentication
  if (authenticated === null) {
    return <div>Loading...</div>;
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={authenticated ? <Navigate to="/" /> : <LoginPage />}
      />
      <Route
        path="/"
        element={authenticated ? <HomePage /> : <Navigate to="/login" />}
      />
      <Route
        path="/insights"
        element={authenticated ? <InsightsPage /> : <Navigate to="/login" />}
      />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}

export default App;
