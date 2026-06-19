import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';
import Layout from './components/Layout';
import ContactsPage from './pages/ContactsPage';
import ContactDetailPage from './pages/ContactDetailPage';
import ContactFormPage from './pages/ContactFormPage';

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/contacts" replace /> },
      { path: 'contacts', element: <ContactsPage /> },
      { path: 'contacts/new', element: <ContactFormPage /> },
      { path: 'contacts/:id', element: <ContactDetailPage /> },
      { path: 'contacts/:id/edit', element: <ContactFormPage /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
