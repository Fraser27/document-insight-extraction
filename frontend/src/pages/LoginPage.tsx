import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Header,
  SpaceBetween,
  FormField,
  Input,
  Button,
  Alert,
  Box,
} from '@cloudscape-design/components';
import { signIn, signUp } from '../services/auth';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSignIn = async () => {
    setLoading(true);
    setError(null);

    try {
      await signIn({ email, password });
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Sign in failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await signUp({ email, password, name });
      setSuccess('Account created successfully! Please check your email to verify your account, then sign in.');
      setIsSignUp(false);
      setPassword('');
    } catch (err: any) {
      setError(err.message || 'Sign up failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isSignUp) {
      handleSignUp();
    } else {
      handleSignIn();
    }
  };

  return (
    <Box padding="xxl">
      <div style={{ maxWidth: '400px', margin: '0 auto' }}>
        <Container
          header={
            <Header variant="h1">
              {isSignUp ? 'Create Account' : 'Sign In'}
            </Header>
          }
        >
          <form onSubmit={handleSubmit}>
            <SpaceBetween size="m">
              {error && (
                <Alert type="error" dismissible onDismiss={() => setError(null)}>
                  {error}
                </Alert>
              )}

              {success && (
                <Alert type="success" dismissible onDismiss={() => setSuccess(null)}>
                  {success}
                </Alert>
              )}

              {isSignUp && (
                <FormField label="Name">
                  <Input
                    value={name}
                    onChange={({ detail }) => setName(detail.value)}
                    placeholder="Enter your name"
                  />
                </FormField>
              )}

              <FormField label="Email">
                <Input
                  value={email}
                  onChange={({ detail }) => setEmail(detail.value)}
                  type="email"
                  placeholder="Enter your email"
                  autoComplete="email"
                />
              </FormField>

              <FormField label="Password">
                <Input
                  value={password}
                  onChange={({ detail }) => setPassword(detail.value)}
                  type="password"
                  placeholder="Enter your password"
                  autoComplete={isSignUp ? 'new-password' : 'current-password'}
                />
              </FormField>

              <Button
                variant="primary"
                onClick={isSignUp ? handleSignUp : handleSignIn}
                loading={loading}
                fullWidth
              >
                {isSignUp ? 'Sign Up' : 'Sign In'}
              </Button>

              <Box textAlign="center">
                <Button
                  variant="link"
                  onClick={() => {
                    setIsSignUp(!isSignUp);
                    setError(null);
                    setSuccess(null);
                  }}
                >
                  {isSignUp
                    ? 'Already have an account? Sign in'
                    : "Don't have an account? Sign up"}
                </Button>
              </Box>
            </SpaceBetween>
          </form>
        </Container>
      </div>
    </Box>
  );
};
