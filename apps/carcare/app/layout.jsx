import "./globals.css";
export const metadata={
 title:"CarCare GR | Λύσεις για κάθε πρόβλημα αυτοκινήτου",
 description:"Βρες λύσεις για καθαρισμό, βαφή, θολά φανάρια, ζάντες και παρμπρίζ. Πρακτικός οδηγός και πραγματικά προϊόντα από συνεργαζόμενα καταστήματα.",
 robots:{index:false,follow:false}
};
export default function RootLayout({children}){return <html lang="el"><body>{children}</body></html>}
