"""Creative Automation Pipeline Package"""

from .compliance import check_brand_compliance
from .campaign_utils import check_legal_compliance, LegalComplianceError

__version__ = "1.0.0"
__all__ = ["check_brand_compliance", "check_legal_compliance", "LegalComplianceError"]
