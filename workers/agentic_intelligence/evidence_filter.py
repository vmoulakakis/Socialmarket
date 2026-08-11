import re

NEGATIVE = re.compile(
    r"\b(slip\w*|slid\w*|slide\w*|scratch\w*|peel\w*|delamin\w*|crack\w*|break\w*|broken|loose|"
    r"uncomfort\w*|pressure|headache|fog\w*|glare|distort\w*|fade\w*|damage\w*|fragile|flicker\w*|"
    r"poor\s+(?:fit|quality|coverage|protection|design|durability)|too\s+(?:expensive|small|large|heavy|dark|light|tight|loose)|"
    r"overpriced|missing|lack\w*|cannot|can.?t|doesn.?t\s+work|does\s+not\s+work|hard\s+to|difficult\s+to|"
    r"arriv\w*\s+damaged|heat\s+damage|moisture|not\s+(?:protect|fit|stay|last|bright)|"
    r"γλιστρ\w*|γρατζουν\w*|ξεφλουδ\w*|σπασ\w*|χαλαρ\w*|άβολ\w*|αβολ\w*|θολ\w*|αντηλιά|"
    r"ζημι\w*|εύθραυσ\w*|ευθραυσ\w*|ακριβ\w*|λείπ\w*|δεν\s+(?:λειτουργ\w*|ταιριάζ\w*|κρατά\w*|προστατεύ\w*)|δυσκολ\w*)\b",
    re.I,
)
SPECIFIC_PROBLEM = re.compile(r"\b(problem|issue|πρόβλημα|προβλημα|θέμα|θεμα)\s+(?:with|is|when|στο|στη|με|είναι|ειναι)\b", re.I)
NOISE = re.compile(
    r"\b(in this (?:blog|article)|we.?ll cover|page updated|medically reviewed|share copied|related|popular brands|view all|"
    r"common problems (?:and|you|with)|how to solve them|how to fix them|knowing how to address|"
    r"most .* problems don.?t mean|problems might seem|προβλήματα και λύσεις|σε αυτό το άρθρο|σε αυτο το αρθρο)\b",
    re.I,
)


class ConcretePainMatcher:
    def search(self, text):
        s = str(text or "")
        if len(s) < 35 or len(s) > 700:
            return None
        if NOISE.search(s):
            return None
        if NEGATIVE.search(s):
            return True
        if SPECIFIC_PROBLEM.search(s):
            # A specific problem construction still needs enough content after
            # the generic word to avoid section headings.
            return True if len(s.split()) >= 9 else None
        return None
