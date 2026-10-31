export interface Session {
  id: string;
  name: string;
  email: string;
  role: 'Responsable de almacén';
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthResponse {
  accessToken: string;
  user: Session;
}
