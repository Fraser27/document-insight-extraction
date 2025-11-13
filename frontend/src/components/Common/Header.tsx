import { TopNavigation } from '@cloudscape-design/components';
import { useNavigate } from 'react-router-dom';
import { signOut, getCurrentUser } from '../../services/auth';
import { useEffect, useState } from 'react';

export const Header: React.FC = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState<string>('');

  useEffect(() => {
    const user = getCurrentUser();
    if (user) {
      setUsername(user.getUsername());
    }
  }, []);

  const handleSignOut = () => {
    signOut();
    navigate('/login');
  };

  return (
    <TopNavigation
      identity={{
        href: '/',
        title: 'Document Insight Extraction',
        logo: {
          src: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjMyIiBoZWlnaHQ9IjMyIiByeD0iNCIgZmlsbD0iIzIzMkYzRSIvPgo8cGF0aCBkPSJNOCAxMEgxNlYxMkg4VjEwWiIgZmlsbD0iI0ZGRkZGRiIvPgo8cGF0aCBkPSJNOCAxNUgyNFYxN0g4VjE1WiIgZmlsbD0iI0ZGRkZGRiIvPgo8cGF0aCBkPSJNOCAyMEgyNFYyMkg4VjIwWiIgZmlsbD0iI0ZGRkZGRiIvPgo8L3N2Zz4K',
          alt: 'Document Insight Extraction',
        },
      }}
      utilities={[
        {
          type: 'button',
          text: 'Documentation',
          href: 'https://docs.aws.amazon.com',
          external: true,
          externalIconAriaLabel: ' (opens in a new tab)',
        },
        {
          type: 'menu-dropdown',
          text: username || 'User',
          description: username,
          iconName: 'user-profile',
          items: [
            {
              id: 'signout',
              text: 'Sign out',
            },
          ],
          onItemClick: ({ detail }) => {
            if (detail.id === 'signout') {
              handleSignOut();
            }
          },
        },
      ]}
      i18nStrings={{
        searchIconAriaLabel: 'Search',
        searchDismissIconAriaLabel: 'Close search',
        overflowMenuTriggerText: 'More',
        overflowMenuTitleText: 'All',
        overflowMenuBackIconAriaLabel: 'Back',
        overflowMenuDismissIconAriaLabel: 'Close menu',
      }}
    />
  );
};
