import re
import os

class SurgicalSecurityGuard:
    def __init__(self, custom_denylist=None):
        # Default patterns for drawing IDs, Project IDs, etc.
        self.patterns = [
            r'[A-Z]{1,2}-\d{4,}',        # e.g., AB-1234, ABC-99999 (Drawings)
            r'P\d{4}-\d{2}',             # e.g., P2026-01 (Projects)
            r'KW-\d{5,}',                # e.g., KW-10045 (Internal Parts)
            r'0x[0-9a-fA-F]{8,}'         # Hex addresses
        ]
        
        # Keywords that should never leak
        self.denylist = [
            "Internal Use Only",
            "Confidential",
            "Privileged",
            "Drawing Ref",
            "顧客名:",
            "Customer:",
            "見積額",
            "Costing Data"
        ]
        if custom_denylist:
            self.denylist.extend(custom_denylist)

    def scrub(self, text):
        """
        Scrub confidential patterns and keywords from text.
        """
        scrubbed_text = text
        
        # 1. Scrub Patterns
        for pattern in self.patterns:
            scrubbed_text = re.sub(pattern, "[MASKED_ID]", scrubbed_text)
            
        # 2. Scrub Keywords
        for kw in self.denylist:
            # Case insensitive replacement
            reg = re.compile(re.escape(kw), re.IGNORECASE)
            scrubbed_text = reg.sub("[REDACTED]", scrubbed_text)
            
        return scrubbed_text

    def is_safe(self, text):
        """
        Returns True if no patterns or keywords are found.
        """
        for pattern in self.patterns:
            if re.search(pattern, text):
                return False
        for kw in self.denylist:
            if kw.lower() in text.lower():
                return False
        return True

if __name__ == "__main__":
    # Test
    guard = SurgicalSecurityGuard()
    sample = "Project P2026-01 is for Customer: ABC-Corp. See drawing AB-5055. Costing Data: 500k JPY. Internal Use Only."
    print("Original:", sample)
    print("Scrubbed:", guard.scrub(sample))
