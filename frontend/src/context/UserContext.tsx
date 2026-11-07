import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../api/types';
import { api } from '../api/client';

interface UserContextType {
  currentUser: User | null;
  users: User[];
  organisationName: string;
  loading: boolean;
  switchUser: (user: User) => void;
}

const DEFAULT_USERS: User[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    name: 'Alice Admin',
    email: 'alice.admin@abctech.example',
    role: 'admin',
    organisation_id: 'abc-tech',
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    name: 'Carlos Compliance',
    email: 'carlos.compliance@abctech.example',
    role: 'compliance_officer',
    organisation_id: 'abc-tech',
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    name: 'Owen Owner',
    email: 'owen.owner@abctech.example',
    role: 'control_owner',
    organisation_id: 'abc-tech',
  },
  {
    id: '44444444-4444-4444-4444-444444444444',
    name: 'Audrey Auditor',
    email: 'audrey.auditor@abctech.example',
    role: 'auditor',
    organisation_id: 'abc-tech',
  },
];

const UserContext = createContext<UserContextType | undefined>(undefined);

export const UserProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [users, setUsers] = useState<User[]>(DEFAULT_USERS);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [organisationName] = useState<string>('ABC Technologies');
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadUsers() {
      try {
        const fetchedUsers = await api.getUsers();
        if (fetchedUsers && fetchedUsers.length > 0) {
          setUsers(fetchedUsers);
          const savedId = localStorage.getItem('auditmind_user_id');
          const matched = fetchedUsers.find((u) => u.id === savedId);
          // Default to Carlos Compliance or first user
          const initialUser = matched || fetchedUsers.find((u) => u.role === 'compliance_officer') || fetchedUsers[0];
          setCurrentUser(initialUser);
          api.setUserId(initialUser.id);
        } else {
          // Fall back to defaults
          const defaultUser = DEFAULT_USERS[1];
          setCurrentUser(defaultUser);
          api.setUserId(defaultUser.id);
        }
      } catch (err) {
        console.warn('Could not fetch users from backend, using seed defaults:', err);
        const defaultUser = DEFAULT_USERS[1]; // Carlos Compliance
        setCurrentUser(defaultUser);
        api.setUserId(defaultUser.id);
      } finally {
        setLoading(false);
      }
    }
    loadUsers();
  }, []);

  const switchUser = (user: User) => {
    setCurrentUser(user);
    api.setUserId(user.id);
    localStorage.setItem('auditmind_user_id', user.id);
  };

  return (
    <UserContext.Provider
      value={{
        currentUser,
        users,
        organisationName,
        loading,
        switchUser,
      }}
    >
      {children}
    </UserContext.Provider>
  );
};

export const useUser = (): UserContextType => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};
