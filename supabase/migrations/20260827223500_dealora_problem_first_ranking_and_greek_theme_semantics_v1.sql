-- Dealora problem-first ranking v1.
-- During the sparse first-party-label phase, reduce reliance on commission proxy and
-- strengthen demand/supply-gap. Also make active themes bilingual so lexical RAG
-- can match the predominantly Greek product feed.

update ops.product_intelligence_config
set config = jsonb_set(
              jsonb_set(config,'{night_brain,weights,conversion_money}','30'::jsonb,true),
              '{night_brain,weights,demand_supply_gap}','35'::jsonb,true
            ),
    version = version + 1,
    updated_by = 'dealora_problem_first_v1',
    updated_at = now()
where id=1;

update intel.demand_themes set semantic_brief = case slug
  when 'back-to-school-2026' then 'Greek Back-to-School demand. σχολείο μαθητής μαθήτρια γονείς δάσκαλος καθηγητής σχολική τσάντα σακίδιο γραφείο καρέκλα οργάνωση διάβασμα μελέτη τεχνολογία laptop tablet ακουστικά παγούρι lunch box μεταφορά ασφάλεια.'
  when 'bts-ergonomics' then 'Student ergonomics. εργονομία σχολική τσάντα σακίδιο πλάτης καρέκλα γραφείου γραφείο υποπόδιο στήριξη μέσης στάση σώματος άνεση μεταφορά βιβλίων.'
  when 'bts-study-organization' then 'Study organization. οργάνωση γραφείου συρταριέρα ράφι βιβλιοθήκη organizer θήκη καλωδίων planner ημερολόγιο αποθήκευση σχολικά είδη τετράδια κασετίνα.'
  when 'bts-concentration' then 'Concentration and focus. συγκέντρωση διάβασμα μελέτη ακουστικά noise cancelling ωτοασπίδες φωτιστικό γραφείου λάμπα μελέτης χρονόμετρο focus αισθητηριακή ηρεμία.'
  when 'bts-technology' then 'Student technology workflow. laptop tablet chromebook πληκτρολόγιο ποντίκι power bank φορτιστής καλώδιο usb hub πολύπριζο router wifi ακουστικά webcam βάση laptop εκτυπωτής.'
  when 'bts-meal-lunch' then 'School meal and hydration. παγούρι θερμός μπουκάλι νερού lunch box δοχείο φαγητού τάπερ ισοθερμική τσάντα φαγητού σνακ μεταφορά τροφίμων.'
  when 'bts-transport' then 'School transport and daily carrying. σχολική τσάντα σακίδιο τρόλεϊ ανακλαστικό φως ποδηλάτου κράνος ασφάλεια μεταφορά commuting καθημερινή μετακίνηση.'
  when 'bts-university' then 'University student problems. φοιτητής φοιτήτρια πανεπιστήμιο φοιτητικό σπίτι γραφείο καρέκλα router wifi πολύπριζο power bank laptop tablet αποθήκευση μικροσυσκευές οργάνωση.'
  when 'bts-teachers' then 'Teacher and classroom productivity. δάσκαλος καθηγητής εκπαιδευτικός τάξη classroom οργάνωση αποθήκευση εκτυπωτής πλαστικοποιητής projector marker εργονομία γραφείο παραγωγικότητα.'
  when 'student-home-2026' then 'Φοιτητικό σπίτι και πρακτική καθημερινότητα. router wifi πολύπριζο προέκταση φορτιστής γραφείο καρέκλα φωτιστικό αποθήκευση organizer βραστήρας καφετιέρα τοστιέρα air fryer σκούπα ανεμιστήρας αφυγραντήρας μικρός χώρος.'
  else semantic_brief end,
  metadata = coalesce(metadata,'{}'::jsonb) || jsonb_build_object(
    'semantic_language','el+en','problem_first_v1',true,'updated_at',now()
  )
where slug in (
  'back-to-school-2026','bts-ergonomics','bts-study-organization','bts-concentration',
  'bts-technology','bts-meal-lunch','bts-transport','bts-university','bts-teachers','student-home-2026'
);
