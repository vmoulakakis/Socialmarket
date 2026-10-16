'use client';
export default function ErrorPage({reset}){return <main className="semanticConsole"><section className="semanticPanel"><h1>Δεν ήταν δυνατή η φόρτωση</h1><p>Η υπηρεσία δεδομένων μπορεί να μην είναι προσωρινά διαθέσιμη.</p><button onClick={reset}>Δοκιμή ξανά</button></section></main>;}
