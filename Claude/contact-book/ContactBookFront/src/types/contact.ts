export interface Contact {
  id: string;
  firstName: string;
  lastName: string;
  emails?: string[];
  phoneNumbers?: string[];
}

export interface ContactRequest {
  firstName: string;
  lastName: string;
  emails?: string[];
  phoneNumbers?: string[];
}

export interface ProblemDetail {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
}
