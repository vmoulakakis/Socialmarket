"use client";
import {useState} from "react";
const prompts=[
 {emoji:"🌧",label:"Δεν καθαρίζει το παρμπρίζ",text:"Οι υαλοκαθαριστήρες αφήνουν γραμμές και δεν βλέπω καλά στη βροχή",problem:"visibility"},
 {emoji:"⚡",label:"Η μπαταρία αδειάζει",text:"Η μπαταρία του αυτοκινήτου αδειάζει, τι πρέπει να ελέγξω;",problem:"maintenance"},
 {emoji:"✦",label:"Λεκέδες σε καθίσματα",text:"Πώς καθαρίζω με ασφάλεια λεκέδες από υφασμάτινα καθίσματα;",problem:"cleaning"},
 {emoji:"☼",label:"Καμένο φανάρι",text:"Έχω καμένο φανάρι, πώς βρίσκω σωστό τύπο λάμπας;",problem:"lighting"}
];
const euro=x=>Number(x).toLocaleString("el-GR",{style:"currency",currency:"EUR"});
const letters="ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ";
export default function AdvisorPanel(){
 const [question,setQuestion]=useState(""),[history,setHistory]=useState([]),[busy,setBusy]=useState(false),[error,setError]=useState(""),[plate,setPlate]=useState(""),[plateCheck,setPlateCheck]=useState("");
 async function ask(text=question,problem=null){
  const q=text.trim().slice(0,240);if(q.length<4||busy)return;
  setQuestion("");setError("");setBusy(true);setHistory(v=>[...v,{role:"user",text:q}].slice(-10));
  try{
   const response=await fetch("/api/assistant",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({question:q,problem})});
   const data=await response.json();if(!response.ok)throw Error(data.error||"Αδυναμία αναζήτησης.");
   setHistory(v=>[...v,{role:"assistant",text:data.answer,products:data.products||[],source:data.source,mode:data.mode}].slice(-10));
  }catch(e){setError(String(e.message||"Η αναζήτηση δεν είναι διαθέσιμη."))}finally{setBusy(false)}
 }
 function inspectPlate(){
  const value=plate.toLocaleUpperCase("el-GR").replace(/\s/g,"");
  const matches=new RegExp("^["+letters+"]{3}-?[0-9]{4}$","u").test(value);
  setPlateCheck(matches?"Η μορφή είναι συμβατή με το συνηθισμένο πρότυπο ελληνικής πινακίδας. Δεν πραγματοποιήθηκε αναζήτηση ιδιοκτήτη, οχήματος ή ασφάλισης.":"Η μορφή δεν αντιστοιχεί στο συνηθισμένο πρότυπο ελληνικής πινακίδας. Παράδειγμα: ΑΒΧ-1234.");
 }
 return <section className="intelligenceStage" id="ai-chat" aria-labelledby="intel-title">
  <div className="intelligenceIntro"><span className="intelligenceEyebrow"><span className="intelligencePing"/> CARCARE INTELLIGENCE / BETA</span><h2 id="intel-title">Ο προσωπικός σου <em>σύμβουλος αυτοκινήτου.</em></h2><p>Από το σύμπτωμα στις διαθέσιμες επιλογές, με ελέγχους ασφαλείας, πραγματικές φωτογραφίες και διαφανή προέλευση κάθε προϊόντος.</p>
   <div className="intelligenceFlow" role="list"><div role="listitem"><b>01</b><span>Περιγράφεις το πρόβλημα</span></div><div role="listitem"><b>02</b><span>Αναζητούμε στη βάση και στο feed</span></div><div role="listitem"><b>03</b><span>Ελέγχεις τη λύση και τη συμβατότητα</span></div></div>
   <div className="aiSignals"><span><i/> Intent routing</span><span><i/> Verified source links</span><span><i/> Safety review</span></div>
   <div className="plateInspector"><div><strong>Έλεγχος μορφής πινακίδας</strong><p>Τοπική επικύρωση · χωρίς ανάκτηση ή αποθήκευση στοιχείων οχήματος.</p></div><div className="plateRow"><label htmlFor="plate-input" className="srOnly">Ελληνική πινακίδα</label><input id="plate-input" value={plate} onChange={e=>{setPlate(e.target.value.slice(0,9));setPlateCheck("")}} placeholder="ΑΒΧ-1234" autoComplete="off"/><button type="button" onClick={inspectPlate}>Έλεγχος ↗</button></div>{plateCheck&&<p className="plateFeedback" role="status">{plateCheck}</p>}</div>
  </div>
  <div className="intelligenceConsole"><div className="consoleTop"><div><span className="consoleIndicator"/><span>CARCARE ADVISOR</span></div><span className="consoleType">EVIDENCE-LED ASSISTANT</span></div>
   <div className="consoleContent" aria-live="polite"><div className="aiWelcome"><span className="aiAvatar">✳</span><div><strong>Τι πρόβλημα αντιμετωπίζεις;</strong><p>Πες μου τι συμβαίνει με το αυτοκίνητό σου. Θα σου δείξω διαθέσιμες επιλογές μόνο όταν υπάρχουν πραγματικά δεδομένα, χωρίς υποθέσεις συμβατότητας.</p></div></div>
   {history.map((m,i)=><div key={i} className={"chatTurn "+(m.role==="user"?"chatUser":"chatAssistant")}><span className="chatRole">{m.role==="user"?"ΕΣΥ":"CARCARE • ΑΠΑΝΤΗΣΗ"}</span><p>{m.text}</p>{m.products?.length>0&&<div className="chatOffers">{m.products.slice(0,3).map((p,j)=><article key={p.id||p.product_id||j} className="chatOffer">{p.image_url&&<img src={p.image_url} alt={p.title} loading="lazy" onError={e=>{e.currentTarget.style.display="none"}}/>}<div><strong>{p.title}</strong><span>{euro(p.price??p.price_eur)}</span><a href={p.tracking_url} target="_blank" rel="sponsored nofollow noopener noreferrer">Προβολή προσφοράς ↗</a></div></article>)}</div>}{m.role==="assistant"&&<span className="chatEvidence">Πηγή: {m.source==="VMDB"?"SocialMarket VMDB":m.source==="Linkwise"?"Linkwise feed":"Χωρίς επιβεβαιωμένες προσφορές"} · Έλεγχος συμβατότητας απαραίτητος</span>}</div>)}
   {busy&&<div className="chatThinking" role="status"><span className="dotPulse"/>Εξετάζουμε τις διαθέσιμες λύσεις…</div>}
   {error&&<p className="chatError" role="alert">{error} <button onClick={()=>setError("")}>Κλείσιμο</button></p>}
   </div>
   <div className="consoleBottom"><div className="promptChips">{prompts.map(p=><button type="button" key={p.label} disabled={busy} onClick={()=>ask(p.text,p.problem)}><span>{p.emoji}</span>{p.label}</button>)}</div>
    <form onSubmit={e=>{e.preventDefault();ask()}} className="chatComposer"><label htmlFor="ai-question" className="srOnly">Περιγραφή προβλήματος</label><input id="ai-question" value={question} onChange={e=>setQuestion(e.target.value)} disabled={busy} maxLength={240} placeholder="Π.χ. δεν ανοίγει το παράθυρο του οδηγού…"/><button type="submit" disabled={busy||question.trim().length<4} aria-label="Αποστολή ερώτησης">↗</button></form><p className="consoleDisclosure">Οι προτάσεις είναι πληροφοριακές, όχι πιστοποιημένη τεχνική διάγνωση. Affiliate σύνδεσμοι μόνο για πραγματικές προσφορές.</p></div>
  </div>
 </section>
}
