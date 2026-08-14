from __future__ import annotations

from typing import Any

from workers.agentic_intelligence.model_router import FreeModelRouter

from .common import load_skill


PLATFORM_RULES = {
    "instagram": {"format": "1080x1350", "hashtags": 6, "qr_allowed": True},
    "facebook": {"format": "1080x1350", "hashtags": 2, "qr_allowed": True},
    "tiktok": {"format": "1080x1920", "hashtags": 5, "qr_allowed": False},
    "linkedin": {"format": "1200x1200", "hashtags": 3, "qr_allowed": True},
}


class MarketingBrain:
    def __init__(self) -> None:
        self.router = FreeModelRouter(max_calls=4)
        self.offer_skill = load_skill("offer-architect")
        self.copy_skill = load_skill("conversion-copywriter")
        self.platform_skill = load_skill("social-platform-strategist")
        self.creative_skill = load_skill("creative-director")

    def _facts(self, product: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
        return {
            "product": {
                "id": product.get("id"), "name": product.get("product_name"), "brand": product.get("brand_name"),
                "merchant": product.get("merchant_name"), "category": product.get("category_raw"),
                "price": product.get("price"), "full_price": product.get("full_price"), "discount_pct": product.get("discount_pct"),
                "availability": product.get("availability"), "tracking_url": product.get("tracking_url"),
                "purchase_friction": product.get("purchase_friction"), "valid_to": product.get("valid_to"),
            },
            "landing_evidence": evidence.get("facts") or {},
        }

    def angles(self, product: dict[str, Any], evidence: dict[str, Any], opportunity: dict[str, Any] | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        facts = self._facts(product, evidence)
        payload = {"facts": facts, "opportunity_scores": opportunity or {}, "required_angle_count": 5}
        system = self.offer_skill + "\nUse Greek for consumer-facing text unless the product context strongly requires English."
        out, telemetry = self.router.complete_json(system, payload, temperature=0.25)
        rows = out.get("angles") if isinstance(out, dict) else None
        if isinstance(rows, list) and rows:
            return rows[:7], telemetry
        name = product.get("product_name") or "το προϊόν"
        price = product.get("price")
        discount = product.get("discount_pct")
        proof = []
        if price is not None:
            proof.append(f"Τιμή €{float(price):.2f}")
        if discount is not None and float(discount) > 0:
            proof.append(f"Έκπτωση {float(discount):.0f}%")
        return [
            {"angle_key":"problem-solution","framework":"PAS","persona":"πρακτικός αγοραστής","hook":f"Το {name} λύνει ένα πολύ συγκεκριμένο καθημερινό πρόβλημα.","promise":"Πρακτική λύση με ξεκάθαρη χρήση.","proof_points":proof,"objections":[],"cta":"Δες τις λεπτομέρειες","score":78,"rationale":"deterministic evidence-safe fallback"},
            {"angle_key":"value","framework":"4Ps","persona":"value seeker","hook":f"Αν έψαχνες {name}, αυτό το offer αξίζει σύγκριση.","promise":"Εστίαση στην αξία της διαθέσιμης προσφοράς.","proof_points":proof,"objections":[],"cta":"Έλεγξε την προσφορά","score":74,"rationale":"deterministic evidence-safe fallback"},
            {"angle_key":"use-case","framework":"JTBD","persona":"use-case buyer","hook":f"Πότε έχει πραγματικά νόημα το {name};","promise":"Δείχνουμε το σωστό use case αντί για γενικά slogans.","proof_points":proof,"objections":[],"cta":"Δες αν σου ταιριάζει","score":72,"rationale":"deterministic evidence-safe fallback"},
        ], {"route":"deterministic_fallback","status":"ok","cost_usd":0}

    def variants(self, product: dict[str, Any], evidence: dict[str, Any], angle: dict[str, Any], platforms: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        facts = self._facts(product, evidence)
        rules = {p: PLATFORM_RULES[p] for p in platforms if p in PLATFORM_RULES}
        payload = {"facts": facts, "selected_angle": angle, "platform_rules": rules, "variants_per_platform": 3}
        system = self.copy_skill + "\n" + self.platform_skill + "\n" + self.creative_skill + "\nReturn genuinely different variants. Use the exact facts only."
        out, telemetry = self.router.complete_json(system, payload, temperature=0.35)
        rows = out.get("variants") if isinstance(out, dict) else None
        if isinstance(rows, list) and rows:
            clean = []
            for i, row in enumerate(rows):
                p = str(row.get("platform") or "").lower()
                if p not in rules:
                    continue
                row.setdefault("variant_key", f"{p}-{i+1}")
                row.setdefault("media_format", rules[p]["format"])
                row.setdefault("disclosure", "Affiliate / διαφημιστικό περιεχόμενο")
                row.setdefault("hashtags", [])
                row.setdefault("creative_direction", {})
                clean.append(row)
            if clean:
                return clean[: max(4, len(platforms)*3)], telemetry
        name = product.get("product_name") or "το προϊόν"
        price = product.get("price")
        price_text = f" · €{float(price):.2f}" if price is not None else ""
        result = []
        for p in platforms:
            if p not in rules:
                continue
            for n, style in enumerate(("direct","use-case","curiosity"), 1):
                hook = angle.get("hook") or f"Δες το {name}"
                if style == "use-case":
                    hook = f"Πότε αξίζει πραγματικά το {name};"
                elif style == "curiosity":
                    hook = f"Ένα χρήσιμο find: {name}"
                caption = f"{hook}\n\n{name}{price_text}. {angle.get('promise') or ''}\n\n{angle.get('cta') or 'Δες περισσότερα.'}".strip()
                result.append({"variant_key":f"{p}-{style}","platform":p,"headline":hook[:90],"hook":hook,"caption":caption,"hashtags":[],"cta":angle.get("cta") or "Δες περισσότερα","disclosure":"Affiliate / διαφημιστικό περιεχόμενο","media_format":rules[p]["format"],"creative_direction":{"family":"premium-minimal" if n==1 else "utility","qr_allowed":rules[p]["qr_allowed"]}})
        return result, {"route":"deterministic_fallback","status":"ok","cost_usd":0}
