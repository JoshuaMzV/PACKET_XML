"""
Packet Tracer File and XML Generator
Delegates XML construction to the unified XMLExporter from Network IR.
"""

from typing import Dict, Any
from exporters import XMLExporter

class PKTBuilder:
    """
    Constructs Packet Tracer XML schema definitions and exports .pkt / .xml files.
    """

    @classmethod
    def generate_pt_xml(cls, topology: Dict[str, Any]) -> str:
        """
        Generates an XML tree compliant with Packet Tracer topology specifications.
        """
        return XMLExporter.export(topology)

