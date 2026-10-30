import unittest
from workers.product_intelligence.graphrag_multilingual_e5 import (
    normalize_vector,encode_query,encode_passages,DIMS,MODEL_ID
)
class FakeModel:
    def encode(self,inputs,**kwargs):
        self.inputs=inputs
        return [[1.0]+[0.0]*(DIMS-1) for _ in inputs]
class MultilingualE5Contract(unittest.TestCase):
    def test_model_and_shape(self):
        self.assertEqual(MODEL_ID,"intfloat/multilingual-e5-small")
        self.assertEqual(DIMS,384)
    def test_query_prefix_greek(self):
        m=FakeModel()
        self.assertEqual(len(encode_query(m,"κάμερα αποχέτευσης")),384)
        self.assertEqual(m.inputs[0],"query: κάμερα αποχέτευσης")
    def test_passage_prefix(self):
        m=FakeModel()
        v=encode_passages(m,["Έξυπνος αισθητήρας υγρασίας","Smart sensor"])
        self.assertEqual(len(v),2)
        self.assertEqual(m.inputs[0],"passage: Έξυπνος αισθητήρας υγρασίας")
    def test_invalid_vector_rejected(self):
        with self.assertRaises(ValueError):
            normalize_vector([0.0]*DIMS)
        with self.assertRaises(ValueError):
            normalize_vector([1.0])
    def test_no_mismatched_dimensions(self):
        with self.assertRaises(ValueError):
            normalize_vector([0.0]*1536)
if __name__=="__main__":
    unittest.main()
