import { Link } from 'react-router-dom';
import type { Contact } from '../types/contact';

interface Props {
  contact: Contact;
  onDeleteClick: (contact: Contact) => void;
}

function initials(c: Contact): string {
  return `${c.firstName.charAt(0)}${c.lastName.charAt(0)}`.toUpperCase();
}

export default function ContactCard({ contact, onDeleteClick }: Props) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-shadow p-4">
      <div className="flex items-start gap-4">
        <div className="w-11 h-11 rounded-full bg-blue-600 text-white flex items-center justify-center text-base font-bold flex-shrink-0 select-none">
          {initials(contact)}
        </div>
        <div className="flex-1 min-w-0">
          <Link
            to={`/contacts/${contact.id}`}
            className="block font-semibold text-gray-900 dark:text-slate-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors truncate"
          >
            {contact.firstName} {contact.lastName}
          </Link>
          {contact.emails?.[0] && (
            <p className="text-sm text-gray-500 dark:text-slate-400 truncate mt-0.5">{contact.emails[0]}</p>
          )}
          {contact.phoneNumbers?.[0] && (
            <p className="text-sm text-gray-500 dark:text-slate-400 mt-0.5">{contact.phoneNumbers[0]}</p>
          )}
        </div>
        <div className="flex gap-1 flex-shrink-0">
          <Link
            to={`/contacts/${contact.id}/edit`}
            className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-slate-700 rounded-lg transition-colors"
            title="Edit"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
          </Link>
          <button
            onClick={() => onDeleteClick(contact)}
            className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-slate-700 rounded-lg transition-colors"
            title="Delete"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
