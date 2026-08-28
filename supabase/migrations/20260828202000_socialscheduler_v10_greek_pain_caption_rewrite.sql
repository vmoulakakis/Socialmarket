-- SocialScheduler v10: rewrite active recovery captions to Greek pain-first marketing copy.

update publish.outbox o
set caption = case
  when (coalesce(ci.title,'') || ' ' || coalesce(ci.metadata->>'category','')) ~* '(cctv|camera|κάμερα|security|ασφαλ)' then
    case lower(o.platform)
      when 'linkedin' then 'Αν έχεις σπίτι, εξοχικό ή μικρό επαγγελματικό χώρο, η ασφάλεια δεν χρειάζεται να ξεκινάει από ακριβή εγκατάσταση. Αυτό το CCTV kit είναι επιλογή που αξίζει έλεγχο για remote επίβλεψη και βασική προστασία. Δες χαρακτηριστικά, διαθεσιμότητα και τελικό κόστος πριν αγοράσεις.'
      when 'tiktok' then 'Έχεις εξοχικό ή μαγαζί και θες να βλέπεις τι γίνεται από το κινητό; 👀 Αυτό το CCTV kit είναι μια πρακτική λύση που αξίζει να δεις πριν πληρώσεις ακριβή εγκατάσταση.'
      when 'instagram' then 'Έχεις σπίτι, εξοχικό ή μικρό χώρο που θες να παρακολουθείς εύκολα; Αυτό το CCTV kit ξεχωρίζει ως πρακτική λύση ασφάλειας με δυνατό value. Δες πρώτα χαρακτηριστικά και τελικό κόστος.'
      else 'Έχεις εξοχικό, σπίτι ή μικρό επαγγελματικό χώρο και θες βασική ασφάλεια χωρίς υπερβολικό κόστος; Αυτό το CCTV kit είναι πρακτική λύση που αξίζει να δεις. Έλεγξε χαρακτηριστικά, διαθεσιμότητα και τελικό κόστος.'
    end
  when (coalesce(ci.title,'') || ' ' || coalesce(ci.metadata->>'category','')) ~* '(robot|πισίνα)' then
    case lower(o.platform)
      when 'linkedin' then 'High-ticket test: για εξοχικά, μικρά καταλύματα ή κατοικίες με πισίνα, το κόστος/χρόνος καθαρισμού γίνεται recurring pain. Αυτό το ρομπότ πισίνας είναι niche λύση υψηλής αξίας· αξίζει έλεγχο μόνο αν υπάρχει πραγματική ανάγκη καθαρισμού και budget.'
      when 'tiktok' then 'Έχεις πισίνα και ο καθαρισμός τρώει χρόνο κάθε εβδομάδα; Αυτό το ρομπότ πισίνας είναι high-ticket λύση για όσους θέλουν λιγότερη ταλαιπωρία και πιο σταθερό καθάρισμα. Δες αν ταιριάζει στις ανάγκες σου.'
      when 'instagram' then 'Για όσους έχουν πισίνα, το πραγματικό κόστος δεν είναι μόνο η αγορά — είναι ο χρόνος και η συντήρηση κάθε εβδομάδα. Αυτό το ρομπότ πισίνας είναι high-ticket επιλογή που αξίζει έλεγχο αν θέλεις αυτοματοποίηση.'
      else 'Έχεις πισίνα και κουράστηκες με τον συνεχή καθαρισμό; Αυτό το ρομπότ πισίνας είναι high-ticket λύση για να μειώσεις χρόνο και ταλαιπωρία. Δες χαρακτηριστικά και αν ταιριάζει στο μέγεθος/ανάγκη σου.'
    end
  when (coalesce(ci.title,'') || ' ' || coalesce(ci.metadata->>'category','')) ~* '(car|auto|αυτοκιν|bluetooth|gps|audio)' then
    case lower(o.platform)
      when 'linkedin' then 'Πρακτική αναβάθμιση αυτοκινήτου: όταν ένα παλιότερο αυτοκίνητο δεν έχει σύγχρονη οθόνη, Bluetooth ή GPS, μια 2DIN λύση μπορεί να βελτιώσει καθημερινή χρήση χωρίς αλλαγή οχήματος. Δες συμβατότητα πριν αγοράσεις.'
      when 'tiktok' then 'Το αυτοκίνητο δεν έχει Bluetooth, GPS ή καλή οθόνη; 🚗 Μια 2DIN λύση μπορεί να το κάνει πολύ πιο πρακτικό στην καθημερινότητα. Πριν αγοράσεις, έλεγξε συμβατότητα και διαστάσεις.'
      when 'instagram' then 'Αν το αυτοκίνητό σου είναι λειτουργικό αλλά τεχνολογικά παλιό, μια 2DIN οθόνη με Bluetooth/GPS μπορεί να αλλάξει την καθημερινή χρήση. Δες συμβατότητα, σύνδεση και τελικό κόστος.'
      else 'Έχεις παλιότερο αυτοκίνητο χωρίς Bluetooth, GPS ή σύγχρονη οθόνη; Αυτή η 2DIN λύση μπορεί να αναβαθμίσει την καθημερινή χρήση χωρίς να αλλάξεις αυτοκίνητο. Έλεγξε συμβατότητα πριν αγοράσεις.'
    end
  when (coalesce(ci.title,'') || ' ' || coalesce(ci.metadata->>'category','')) ~* '(led|φωτισ)' then
    case lower(o.platform)
      when 'linkedin' then 'Για σπίτι, γραφείο ή μικρό επαγγελματικό χώρο, ο φωτισμός αλλάζει άμεσα την εικόνα του χώρου. Αυτό το LED φωτιστικό είναι επιλογή για πιο καθαρό, μοντέρνο αποτέλεσμα με ενσωματωμένο φωτισμό. Δες διαστάσεις και τελικό κόστος.'
      when 'tiktok' then 'Θες ο χώρος να δείχνει πιο μοντέρνος χωρίς μεγάλη ανακαίνιση; 💡 Ένα σωστό LED φωτιστικό μπορεί να αλλάξει αμέσως την εικόνα του δωματίου. Δες αν ταιριάζει στις διαστάσεις σου.'
      when 'instagram' then 'Μικρή αλλαγή, μεγάλο οπτικό αποτέλεσμα: ένα μοντέρνο LED φωτιστικό μπορεί να αναβαθμίσει σαλόνι, γραφείο ή επαγγελματικό χώρο. Δες διαστάσεις, φωτεινότητα και τελικό κόστος.'
      else 'Θες να αλλάξει η εικόνα του χώρου χωρίς μεγάλη ανακαίνιση; Ένα μοντέρνο LED φωτιστικό μπορεί να δώσει καθαρότερο και πιο σύγχρονο αποτέλεσμα. Δες διαστάσεις και τελικό κόστος πριν αγοράσεις.'
    end
  else o.caption
end,
executor_metadata = coalesce(o.executor_metadata, '{}'::jsonb) || jsonb_build_object(
  'caption_rewrite', jsonb_build_object('policy','v10-greek-pain-first','rewritten_at',now())
),
updated_at = now()
from content.items ci
where ci.id = o.content_item_id
  and o.status in ('approved','leased','scheduled')
  and o.executor_metadata->>'legacy_safe_bridge' = 'true';

update ops.socialscheduler_config
set config = config || jsonb_build_object(
      'caption_policy', 'v10-greek-pain-first',
      'caption_policy_updated_at', to_jsonb(now())
    ),
    version = version + 1,
    updated_by = 'socialscheduler_v10_greek_pain_caption_rewrite',
    updated_at = now()
where id = 1;
