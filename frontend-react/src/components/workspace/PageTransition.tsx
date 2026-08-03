interface PageTransitionProps {
  children: React.ReactNode;
  transitionKey: string;
}

export function PageTransition({ children, transitionKey }: PageTransitionProps) {
  return (
    <div
      className="page-transition flex-1 overflow-hidden"
      key={transitionKey}
    >
      {children}
    </div>
  );
}
