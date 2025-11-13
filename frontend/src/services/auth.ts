import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserAttribute,
  CognitoUserSession,
} from 'amazon-cognito-identity-js';

const USER_POOL_ID = import.meta.env.VITE_USER_POOL_ID || '';
const CLIENT_ID = import.meta.env.VITE_USER_POOL_CLIENT_ID || '';

const poolData = {
  UserPoolId: USER_POOL_ID,
  ClientId: CLIENT_ID,
};

const userPool = new CognitoUserPool(poolData);

export interface SignUpParams {
  email: string;
  password: string;
  name?: string;
}

export interface SignInParams {
  email: string;
  password: string;
}

export interface AuthTokens {
  idToken: string;
  accessToken: string;
  refreshToken: string;
}

// Sign up a new user
export const signUp = (params: SignUpParams): Promise<CognitoUser> => {
  return new Promise((resolve, reject) => {
    const { email, password, name } = params;
    
    const attributeList: CognitoUserAttribute[] = [
      new CognitoUserAttribute({
        Name: 'email',
        Value: email,
      }),
    ];

    if (name) {
      attributeList.push(
        new CognitoUserAttribute({
          Name: 'name',
          Value: name,
        })
      );
    }

    userPool.signUp(email, password, attributeList, [], (err, result) => {
      if (err) {
        reject(err);
        return;
      }
      if (result?.user) {
        resolve(result.user);
      } else {
        reject(new Error('Sign up failed'));
      }
    });
  });
};

// Sign in an existing user
export const signIn = (params: SignInParams): Promise<CognitoUserSession> => {
  return new Promise((resolve, reject) => {
    const { email, password } = params;

    const authenticationDetails = new AuthenticationDetails({
      Username: email,
      Password: password,
    });

    const userData = {
      Username: email,
      Pool: userPool,
    };

    const cognitoUser = new CognitoUser(userData);

    cognitoUser.authenticateUser(authenticationDetails, {
      onSuccess: (session) => {
        // Store tokens in localStorage
        storeTokens({
          idToken: session.getIdToken().getJwtToken(),
          accessToken: session.getAccessToken().getJwtToken(),
          refreshToken: session.getRefreshToken().getToken(),
        });
        resolve(session);
      },
      onFailure: (err) => {
        reject(err);
      },
    });
  });
};

// Sign out the current user
export const signOut = (): void => {
  const cognitoUser = userPool.getCurrentUser();
  if (cognitoUser) {
    cognitoUser.signOut();
  }
  clearTokens();
};

// Get the current authenticated user
export const getCurrentUser = (): CognitoUser | null => {
  return userPool.getCurrentUser();
};

// Get current session
export const getCurrentSession = (): Promise<CognitoUserSession> => {
  return new Promise((resolve, reject) => {
    const cognitoUser = getCurrentUser();
    
    if (!cognitoUser) {
      reject(new Error('No user found'));
      return;
    }

    cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err) {
        reject(err);
        return;
      }
      if (session && session.isValid()) {
        resolve(session);
      } else {
        reject(new Error('Invalid session'));
      }
    });
  });
};

// Refresh the session using refresh token
export const refreshSession = (): Promise<CognitoUserSession> => {
  return new Promise((resolve, reject) => {
    const cognitoUser = getCurrentUser();
    
    if (!cognitoUser) {
      reject(new Error('No user found'));
      return;
    }

    cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err) {
        reject(err);
        return;
      }

      if (!session) {
        reject(new Error('No session found'));
        return;
      }

      const refreshToken = session.getRefreshToken();
      
      cognitoUser.refreshSession(refreshToken, (refreshErr, newSession) => {
        if (refreshErr) {
          reject(refreshErr);
          return;
        }
        
        // Update stored tokens
        storeTokens({
          idToken: newSession.getIdToken().getJwtToken(),
          accessToken: newSession.getAccessToken().getJwtToken(),
          refreshToken: newSession.getRefreshToken().getToken(),
        });
        
        resolve(newSession);
      });
    });
  });
};

// Get ID token (for API authentication)
export const getIdToken = async (): Promise<string> => {
  try {
    const session = await getCurrentSession();
    return session.getIdToken().getJwtToken();
  } catch (error) {
    // Try to refresh the session
    try {
      const newSession = await refreshSession();
      return newSession.getIdToken().getJwtToken();
    } catch (refreshError) {
      throw new Error('Failed to get valid token');
    }
  }
};

// Store tokens in localStorage
const storeTokens = (tokens: AuthTokens): void => {
  localStorage.setItem('idToken', tokens.idToken);
  localStorage.setItem('accessToken', tokens.accessToken);
  localStorage.setItem('refreshToken', tokens.refreshToken);
};

// Clear tokens from localStorage
const clearTokens = (): void => {
  localStorage.removeItem('idToken');
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
};

// Check if user is authenticated
export const isAuthenticated = async (): Promise<boolean> => {
  try {
    await getCurrentSession();
    return true;
  } catch {
    return false;
  }
};
