/// <reference types="vite/client" />

declare namespace React {
  interface HTMLAttributes<T> {
    toolname?: string;
    tooldescription?: string;
    toolparamdescription?: string;
  }

  interface InputHTMLAttributes<T> {
    toolparamdescription?: string;
  }

  interface TextareaHTMLAttributes<T> {
    toolparamdescription?: string;
  }

  interface SelectHTMLAttributes<T> {
    toolparamdescription?: string;
  }
}
