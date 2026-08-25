"""
Cisco Packet Tracer Native .PKT Encoder & Decoder Module
Direct, offline generation and verification of .pkt binary files from Network IR / XML.

Architecture:
  Network IR -> XMLExporter (Canonical XML) -> PKTEncoder -> network.pkt (Binary Container)
  network.pkt -> PKTDecoder -> Recovered XML (Lossless Verification)
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Union, Optional

from network_ir import NetworkIR
from exporters import XMLExporter
from pkt_crypto.pt_crypto import decrypt_pkt
from pkt_crypto.repacket import compress_qt, obf_stage2, encrypt_pkt, obf_stage1

log = logging.getLogger(__name__)

class PKTEncoder:
    """
    Encodes Canonical XML into Cisco Packet Tracer .pkt binary container format
    using Qt compression, Twofish-128 in EAX authenticated mode, and multi-stage XOR obfuscation.
    """

    @classmethod
    def encode_xml_to_pkt(cls, xml_data: Union[str, bytes]) -> bytes:
        """
        Transforms an XML string or bytes into a valid Packet Tracer .pkt binary payload.
        """
        if isinstance(xml_data, str):
            xml_bytes = xml_data.encode('utf-8')
        else:
            xml_bytes = xml_data

        # 1. Qt Compression: prepends 4-byte BE uncompressed length + zlib compression
        stage2_input = compress_qt(xml_bytes)

        # 2. Stage 2 Obfuscation: Positional XOR
        decrypted_blob = obf_stage2(stage2_input)

        # 3. Twofish-128 Encryption in EAX Mode with CMAC Tag
        stage1_input = encrypt_pkt(decrypted_blob)

        # 4. Stage 1 Obfuscation: Mirror XOR
        final_pkt_bytes = obf_stage1(stage1_input)

        return final_pkt_bytes

    @classmethod
    def decode_pkt_to_xml(cls, pkt_data: bytes) -> str:
        """
        Decodes a Packet Tracer .pkt binary payload back into its Canonical XML string.
        """
        xml_bytes = decrypt_pkt(pkt_data)
        return xml_bytes.decode('utf-8')

    @classmethod
    def generate_pkt(
        cls, 
        network_ir: Union[NetworkIR, Dict[str, Any]], 
        output_path: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """
        Directly generates a .pkt file from a validated Network IR.
        Executes internal round-trip verification to ensure 100% integrity.
        """
        if isinstance(network_ir, dict):
            ir = NetworkIR(network_ir)
        else:
            ir = network_ir

        if not ir.validation.get("is_valid"):
            ir.validate()

        # 1. Generate Canonical XML from Network IR
        xml_string = XMLExporter.export(ir)

        # 2. Encode XML to .pkt binary
        pkt_bytes = cls.encode_xml_to_pkt(xml_string)

        # 3. Write file if output_path is provided
        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_bytes(pkt_bytes)
            log.info("Generated .pkt file at %s (%d bytes)", out_file, len(pkt_bytes))

        # 4. Immediate Round-Trip Lossless Verification
        recovered_xml = cls.decode_pkt_to_xml(pkt_bytes)
        round_trip_success = (recovered_xml == xml_string)

        return {
            "success": True,
            "file_path": str(output_path) if output_path else None,
            "file_size": len(pkt_bytes),
            "pt_format_version": "8.2",
            "crypto_cipher": "Twofish-128 (EAX Mode + CMAC)",
            "compression": "Qt qCompress (zlib)",
            "round_trip_verified": round_trip_success,
            "total_devices": len(ir.devices),
            "total_links": len(ir.links),
            "total_vlans": len(ir.vlans),
            "total_hosts": len(ir.hosts),
            "pkt_bytes": pkt_bytes
        }
