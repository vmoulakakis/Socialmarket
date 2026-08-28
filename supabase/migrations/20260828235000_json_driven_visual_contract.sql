-- JSON-driven post visual contract for fully automatic problem-solver creatives.
-- The creative layer must write visual_contract JSON into each variant; the renderer
-- consumes that JSON and produces the final image without manual editing.

update ops.product_intelligence_config
set config = config || jsonb_build_object(
      'post_visual_contract_version', 'problem_solver_large_qr_v2_json_driven',
      'post_visual_contract_required', true,
      'post_visual_contract_json_schema', jsonb_build_object(
        'required_variant_keys', jsonb_build_array('id', 'visual_contract'),
        'supported_variant_ids', jsonb_build_array('feed_4x5', 'reel_9x16', 'square_1x1'),
        'visual_contract_required_keys', jsonb_build_array(
          'layout',
          'eyebrow',
          'pain_headline',
          'solution_line',
          'benefits',
          'cta',
          'qr_label',
          'qr_size_ratio',
          'trust_line',
          'footer'
        ),
        'layout', 'problem_solver_large_qr_v1',
        'benefits_exact_count', 3,
        'qr_size_ratio_min', 0.20,
        'qr_size_ratio_target', 0.24,
        'qr_size_ratio_max', 0.28,
        'rules', jsonb_build_array(
          'problem_first_not_catalogue_first',
          'real_product_image_only',
          'large_scannable_qr_required',
          'affiliate_disclosure_required',
          'no_fake_urgency',
          'no_invented_product_features',
          'cta_must_point_to_scan_or_details'
        )
      ),
      'post_visual_contract_default', jsonb_build_object(
        'layout', 'problem_solver_large_qr_v1',
        'eyebrow', 'DEALORA AI · ΕΞΥΠΝΗ ΠΡΟΤΑΣΗ',
        'pain_headline', 'Ποιο πρόβλημα λύνει αυτό για σένα;',
        'solution_line', 'Δες αν ταιριάζει στην ανάγκη σου πριν αγοράσεις.',
        'benefits', jsonb_build_array(
          'Λύνει συγκεκριμένο καθημερινό πρόβλημα',
          'Καθαρή επιλογή χωρίς περίπλοκη αναζήτηση',
          'Δες λεπτομέρειες πριν αγοράσεις'
        ),
        'cta', 'Σκάναρε & δες λεπτομέρειες',
        'qr_label', 'ΣΚΑΝΑΡΕ ΕΔΩ',
        'qr_size_ratio', 0.24,
        'trust_line', 'Ελεγμένο affiliate προϊόν · δες λεπτομέρειες πριν αγοράσεις',
        'footer', 'Διαφημιστικός / affiliate σύνδεσμος'
      ),
      'post_visual_contract_category_templates', jsonb_build_object(
        'security', jsonb_build_object(
          'pain_headline', 'Θες να βλέπεις τον χώρο σου όπου κι αν είσαι;',
          'solution_line', 'Πρακτική λύση για σπίτι, εξοχικό ή μικρό επαγγελματικό χώρο.',
          'benefits', jsonb_build_array('Live εικόνα από κινητό', 'Καταγραφή & έλεγχος', 'Πιο ήσυχο κεφάλι όταν λείπεις')
        ),
        'pool_robot', jsonb_build_object(
          'pain_headline', 'Κουράστηκες να ασχολείσαι συνέχεια με την πισίνα;',
          'solution_line', 'Αυτόματη λύση καθαρισμού για εξοχικό, βίλα ή επαγγελματικό χώρο.',
          'benefits', jsonb_build_array('Λιγότερος κόπος', 'Πιο σταθερή καθαριότητα', 'Χρήσιμο για εξοχικό ή βίλα')
        ),
        'lighting', jsonb_build_object(
          'pain_headline', 'Θες να αλλάξει ο χώρος χωρίς ανακαίνιση;',
          'solution_line', 'Μία σωστή επιλογή φωτισμού μπορεί να αλλάξει αμέσως την εικόνα του χώρου.',
          'benefits', jsonb_build_array('Πιο μοντέρνα εικόνα', 'Άμεση αλλαγή ατμόσφαιρας', 'Καθαρό look με LED')
        ),
        'car_audio', jsonb_build_object(
          'pain_headline', 'Το αυτοκίνητο δείχνει παλιό μέσα;',
          'solution_line', 'Αναβάθμιση καθημερινής χρήσης με οθόνη, σύνδεση και πιο έξυπνη πλοήγηση.',
          'benefits', jsonb_build_array('Οθόνη αφής', 'Bluetooth / GPS / USB', 'Πιο έξυπνη καθημερινή χρήση')
        ),
        'home_office', jsonb_build_object(
          'pain_headline', 'Δουλεύεις πολλές ώρες σε άβολο setup;',
          'solution_line', 'Πρακτική λύση για πιο οργανωμένο και άνετο καθημερινό χώρο εργασίας.',
          'benefits', jsonb_build_array('Καλύτερη καθημερινότητα', 'Πιο οργανωμένο γραφείο', 'Χρήσιμο για σπίτι ή δουλειά')
        )
      ),
      'post_visual_contract_updated_at', to_jsonb(now())
    ),
    version = version + 1,
    updated_by = 'json_driven_visual_contract_v2',
    updated_at = now()
where id = 1;

update ops.socialscheduler_config
set config = config || jsonb_build_object(
      'post_visual_contract_version', 'problem_solver_large_qr_v2_json_driven',
      'requires_renderer_visual_contract', true,
      'renderer_primary', 'internal_pillow_json_visual_contract',
      'external_template_reference_only', true,
      'manual_design_edit_required', false,
      'post_image_must_be_generated_from_json', true,
      'visual_contract_minimums', jsonb_build_object(
        'benefits_exact_count', 3,
        'qr_size_ratio_min', 0.20,
        'qr_size_ratio_target', 0.24,
        'qr_size_ratio_max', 0.28,
        'problem_solver_layout', true,
        'real_product_image_only', true,
        'affiliate_disclosure_required', true
      ),
      'post_visual_contract_updated_at', to_jsonb(now())
    ),
    version = version + 1,
    updated_by = 'json_driven_visual_contract_v2',
    updated_at = now()
where id = 1;
