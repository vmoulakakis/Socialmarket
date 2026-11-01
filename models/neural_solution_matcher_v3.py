"""SocialMarket 3.0: trainable neural product↔pain two-tower architecture.

Not trained by default. Required supervision: independently verified, dated,
human-reviewed problem/product pairs with held-out problem groups. Never train
on a model's own candidate guesses or on raw affiliate commission labels.
"""
from __future__ import annotations
import torch
from torch import nn
import torch.nn.functional as F

DIMS=384
MIN_VERIFIED_PAIRS=100

class NeuralSolutionMatcher(nn.Module):
    def __init__(self, input_dim=DIMS, hidden=256, output_dim=128, temperature=0.07):
        super().__init__()
        if not (0 < temperature <= 1):
            raise ValueError("temperature must be in (0,1]")
        self.problem_net=nn.Sequential(
            nn.LayerNorm(input_dim), nn.Linear(input_dim,hidden),
            nn.GELU(),nn.Linear(hidden,output_dim))
        self.product_net=nn.Sequential(
            nn.LayerNorm(input_dim), nn.Linear(input_dim,hidden),
            nn.GELU(),nn.Linear(hidden,output_dim))
        self.temperature=temperature

    def encode_problem(self, vectors):
        return F.normalize(self.problem_net(vectors),p=2,dim=-1)

    def encode_product(self,vectors):
        return F.normalize(self.product_net(vectors),p=2,dim=-1)

    def forward(self,problem_embedding,product_embedding):
        if problem_embedding.ndim!=2 or product_embedding.ndim!=2:
            raise ValueError("expected 2D E5 vector batch")
        if problem_embedding.shape[1]!=DIMS or product_embedding.shape[1]!=DIMS:
            raise ValueError("E5 model dimension mismatch")
        return self.encode_problem(problem_embedding) @ self.encode_product(product_embedding).T

    def contrastive_loss(self,verified_problem_vectors,verified_product_vectors):
        if verified_problem_vectors.shape[0]!=verified_product_vectors.shape[0]:
            raise ValueError("positive pairs must be aligned")
        batch=verified_problem_vectors.shape[0]
        if batch<2:
            raise ValueError("need at least 2 verified pairs per contrastive batch")
        logits=self(verified_problem_vectors,verified_product_vectors)/self.temperature
        labels=torch.arange(batch,device=logits.device)
        return (F.cross_entropy(logits,labels)+F.cross_entropy(logits.T,labels))/2

def assert_training_eligible(verified_pairs:int, unique_problems:int,
                             unique_products:int, distinct_evidence_groups:int):
    if verified_pairs<MIN_VERIFIED_PAIRS:
        raise RuntimeError("insufficient_independently_verified_product_problem_pairs")
    if unique_problems<10 or unique_products<50:
        raise RuntimeError("insufficient_problem_and_product_diversity")
    if distinct_evidence_groups<3:
        raise RuntimeError("not_enough_independent_evidence_groups")
    return True
