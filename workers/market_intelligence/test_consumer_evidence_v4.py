import unittest

from consumer_evidence_v4 import _consumer_score, _split_segments, source_family


class ConsumerEvidenceV4Tests(unittest.TestCase):
    def test_marketplace_review_with_real_pain_and_category_binding_passes(self):
        text='Αγόρασα το κινητό πριν έναν μήνα αλλά η μπαταρία τελειώνει πολύ γρήγορα και υπερθερμαίνεται.'
        score,pain,purchase,first=_consumer_score(
            text,'Smartphone 5G αξιολογήσεις',['κινητα','smartphone'],'marketplace_review','https://skroutz.gr/s/123'
        )
        self.assertGreaterEqual(score,10)
        self.assertTrue(pain)
        self.assertTrue(purchase)
        self.assertTrue(first)

    def test_navigation_boilerplate_is_rejected(self):
        text='Μετάβαση στο περιεχόμενο. Κανένα προϊόν στο καλάθι. Δημιουργία λογαριασμού.'
        score,_,_,_=_consumer_score(text,'Παιδικά ρούχα',['παιδικα ρουχα'],'public_web','https://shop.example/p/1')
        self.assertEqual(score,0)

    def test_generic_problem_without_taxonomy_binding_is_rejected(self):
        text='Αγόρασα το προϊόν και έχω μεγάλο πρόβλημα με την παράδοση και θέλω επιστροφή.'
        score,_,_,_=_consumer_score(text,'Γενική είδηση αγοράς',['αντηλιακα','αντηλιακο'],'public_web','https://news.example/article/1')
        self.assertEqual(score,0)

    def test_generic_editorial_product_article_is_not_consumer_evidence(self):
        text='Η αγορά των smartphone έχει προβλήματα και οι καταναλωτές αναζητούν καλύτερη μπαταρία και χαμηλότερη τιμή.'
        score,_,_,first=_consumer_score(
            text,'Ειδήσεις: προβλήματα στην αγορά smartphone',['smartphone','κινητα'],'public_web','https://news.example/news/smartphones'
        )
        self.assertEqual(score,0)
        self.assertFalse(first)

    def test_merchant_copy_with_problem_words_is_rejected_without_first_person(self):
        text='Αγορά smartphone σε καλή τιμή. Η νέα μπαταρία λύνει το πρόβλημα υπερθέρμανσης και προσφέρει εγγύηση.'
        score,_,_,first=_consumer_score(
            text,'Smartphone 5G - αγορά online',['smartphone','κινητα'],'public_web','https://merchant.example/product/phone'
        )
        self.assertEqual(score,0)
        self.assertFalse(first)

    def test_real_greek_forum_first_person_problem_passes(self):
        text='Πήρα το smartphone πριν δύο εβδομάδες και έχω πρόβλημα: η μπαταρία τελειώνει γρήγορα και το κινητό υπερθερμαίνεται.'
        score,pain,purchase,first=_consumer_score(
            text,'Smartphone - εμπειρίες χρηστών',['smartphone','κινητα'],'community_forum','https://myphone.gr/forum/topic/123'
        )
        self.assertGreaterEqual(score,10)
        self.assertTrue(pain)
        self.assertTrue(purchase)
        self.assertTrue(first)

    def test_forum_problem_without_purchase_word_can_pass_with_first_person_use(self):
        text='Έχω τα ακουστικά εδώ και μήνες και με ενοχλεί ο θόρυβος όταν αποσυνδέονται, μερικές φορές δεν δουλεύουν καθόλου.'
        score,pain,_,first=_consumer_score(
            text,'Ακουστικά εμπειρίες',['ακουστικα'],'community_forum','https://avsite.gr/forum/threads/headphones.123/'
        )
        self.assertGreaterEqual(score,10)
        self.assertTrue(pain)
        self.assertTrue(first)

    def test_community_blog_editorial_copy_needs_first_person_or_comment_signal(self):
        text='Τα αρώματα συχνά έχουν πρόβλημα διάρκειας και η τιμή αποτελεί σημαντικό κριτήριο αγοράς.'
        score,_,_,first=_consumer_score(
            text,'Αρώματα και διάρκεια',['αρωματα'],'community_blog','https://beautyblog.gr/fragrance-guide'
        )
        self.assertEqual(score,0)
        self.assertFalse(first)

    def test_community_blog_first_person_comment_can_pass(self):
        text='Αγόρασα αυτό το άρωμα και σε μένα η διάρκεια είναι πολύ κακή, τελειώνει γρήγορα και δεν αξίζει την τιμή του. Σχόλια'
        score,pain,purchase,first=_consumer_score(
            text,'Άρωμα - εμπειρίες',['αρωμα'],'community_blog','https://beautyblog.gr/perfume/comments'
        )
        self.assertGreaterEqual(score,10)
        self.assertTrue(pain)
        self.assertTrue(purchase)
        self.assertTrue(first)

    def test_source_family_is_explicit_for_greek_communities(self):
        self.assertEqual(source_family('https://www.skroutz.gr/s/123/test')[0],'marketplace_review')
        self.assertEqual(source_family('https://www.insomnia.gr/forums/topic/123')[0],'community_forum')
        self.assertEqual(source_family('https://www.reddit.com/r/greece/comments/abc')[0],'social_forum')
        self.assertEqual(source_family('https://myphone.gr/forum/topic/123')[0],'community_forum')
        self.assertEqual(source_family('https://www.avsite.gr/forum/threads/123')[0],'community_forum')
        self.assertEqual(source_family('https://forum.4troxoi.gr/topic/123')[0],'community_forum')
        self.assertEqual(source_family('https://forum.mens-only.gr/viewtopic.php?t=123')[0],'community_forum')
        self.assertEqual(source_family('https://beautyblog.gr/post/123')[0],'community_blog')

    def test_segmenter_keeps_real_review_units(self):
        text='Πρώτη σύντομη πρόταση.\nΑγόρασα τη συσκευή και μετά από λίγες μέρες εμφάνισε πρόβλημα με θόρυβο και διαρροή νερού.\nΆλλη παράγραφος που είναι αρκετά μεγάλη για να θεωρηθεί πραγματικό consumer text και όχι navigation.'
        segments=_split_segments(text)
        self.assertTrue(any('διαρροή' in x for x in segments))


if __name__=='__main__':
    unittest.main()
