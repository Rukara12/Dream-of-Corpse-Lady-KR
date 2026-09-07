# -*- coding: utf-8 -*-
"""I2 Localization LanguageSource 바이너리 파서/직렬화."""
import struct

class Reader:
    def __init__(self, data):
        self.data = data
        self.pos  = 0

    def read_int32(self):
        v = struct.unpack_from('<i', self.data, self.pos)[0]; self.pos += 4; return v

    def read_int64(self):
        v = struct.unpack_from('<q', self.data, self.pos)[0]; self.pos += 8; return v

    def read_uint8(self):
        v = struct.unpack_from('<B', self.data, self.pos)[0]; self.pos += 1; return v

    def read_float(self):
        v = struct.unpack_from('<f', self.data, self.pos)[0]; self.pos += 4; return v

    def align4(self):
        self.pos += (4 - self.pos % 4) % 4

    def read_uint8_aligned(self):
        v = self.read_uint8(); self.align4(); return v

    def read_string(self):
        n = self.read_int32()
        s = self.data[self.pos:self.pos + n].decode('utf-8')
        self.pos += n
        self.align4()
        return s


# ================================================================
# 바이너리 Writer
# ================================================================
class Writer:
    def __init__(self):
        self.buf = bytearray()

    def write_int32(self, v):
        self.buf += struct.pack('<i', int(v))

    def write_int64(self, v):
        self.buf += struct.pack('<q', int(v))

    def write_uint8(self, v):
        self.buf += struct.pack('<B', int(v))

    def write_float(self, v):
        self.buf += struct.pack('<f', float(v))

    def align4(self):
        pad = (4 - len(self.buf) % 4) % 4
        self.buf += b'\x00' * pad

    def write_uint8_aligned(self, v):
        self.write_uint8(v); self.align4()

    def write_string(self, s):
        encoded = s.encode('utf-8')
        self.write_int32(len(encoded))
        self.buf += encoded
        self.align4()

    def bytes(self):
        return bytes(self.buf)


# ================================================================
# 바이너리 파싱
# ================================================================
def parse_term(r):
    term = {}
    term['Term']     = r.read_string()
    term['TermType'] = r.read_int32()

    lang_count        = r.read_int32()
    term['Languages'] = [r.read_string() for _ in range(lang_count)]

    flags_count   = r.read_int32()
    term['Flags'] = [r.read_uint8() for _ in range(flags_count)]
    r.align4()

    lt_count                = r.read_int32()
    term['Languages_Touch'] = [r.read_string() for _ in range(lt_count)]

    return term


def parse_all(raw):
    r = Reader(raw)

    header = {}
    header['m_FileID']  = r.read_int32()
    header['m_PathID']  = r.read_int64()
    header['m_Enabled'] = r.read_uint8_aligned()
    header['s_FileID']  = r.read_int32()
    header['s_PathID']  = r.read_int64()
    header['m_Name']    = r.read_string()

    src = {}
    src['UserAgreesToHaveItOnTheScene']            = r.read_uint8_aligned()
    src['UserAgreesToHaveItInsideThePluginsFolder'] = r.read_uint8_aligned()
    src['GoogleLiveSyncIsUptoDate']                = r.read_uint8_aligned()

    terms_count   = r.read_int32()
    src['mTerms'] = [parse_term(r) for _ in range(terms_count)]

    src['IgnoreDeviceLanguage']     = r.read_uint8_aligned()
    src['_AllowUnloadingLanguages'] = r.read_int32()
    src['_UnknownInt32']            = r.read_int32()

    lang_count = r.read_int32()
    langs = []
    for _ in range(lang_count):
        lang = {}
        lang['Name']  = r.read_string()
        lang['Code']  = r.read_string()
        lang['Flags'] = r.read_uint8_aligned()
        langs.append(lang)
    src['mLanguages'] = langs

    src['OnMissingTranslation'] = r.read_int32()
    src['mTerm_AppName']        = r.read_string()

    src['Google_WebServiceURL']         = r.read_string()
    src['Google_SpreadsheetKey']        = r.read_string()
    src['Google_SpreadsheetName']       = r.read_string()
    src['Google_LastUpdatedVersion']    = r.read_string()
    src['GoogleUpdateFrequency']        = r.read_int32()
    src['GoogleInEditorCheckFrequency'] = r.read_int32()
    src['GoogleUpdateSynchronization']  = r.read_int32()
    src['GoogleUpdateDelay']            = r.read_float()

    assets_count = r.read_int32()
    assets = []
    for _ in range(assets_count):
        assets.append({
            'm_FileID': r.read_int32(),
            'm_PathID': r.read_int64()
        })
    src['Assets'] = assets

    print(f"  바이너리 파싱 완료: pos={r.pos} / total={len(raw)} bytes")
    if r.pos != len(raw):
        print(f"  ⚠️ 경고: {len(raw) - r.pos} bytes 남음")

    return {'header': header, 'mSource': src}


# ================================================================
# 바이너리 직렬화
# ================================================================
def serialize_term(w, term):
    w.write_string(term['Term'])
    w.write_int32(term['TermType'])

    langs = term['Languages']
    w.write_int32(len(langs))
    for s in langs:
        w.write_string(s)

    flags = term['Flags']
    w.write_int32(len(flags))
    for f in flags:
        w.write_uint8(f)
    w.align4()

    lt = term['Languages_Touch']
    w.write_int32(len(lt))
    for s in lt:
        w.write_string(s)


def serialize_all(data):
    w = Writer()
    header = data['header']
    src    = data['mSource']

    w.write_int32(header['m_FileID'])
    w.write_int64(header['m_PathID'])
    w.write_uint8_aligned(header['m_Enabled'])
    w.write_int32(header['s_FileID'])
    w.write_int64(header['s_PathID'])
    w.write_string(header['m_Name'])

    w.write_uint8_aligned(src['UserAgreesToHaveItOnTheScene'])
    w.write_uint8_aligned(src['UserAgreesToHaveItInsideThePluginsFolder'])
    w.write_uint8_aligned(src['GoogleLiveSyncIsUptoDate'])

    terms = src['mTerms']
    w.write_int32(len(terms))
    for term in terms:
        serialize_term(w, term)

    w.write_uint8_aligned(src['IgnoreDeviceLanguage'])
    w.write_int32(src['_AllowUnloadingLanguages'])
    w.write_int32(src['_UnknownInt32'])

    langs = src['mLanguages']
    w.write_int32(len(langs))
    for lang in langs:
        w.write_string(lang['Name'])
        w.write_string(lang['Code'])
        w.write_uint8_aligned(lang['Flags'])

    w.write_int32(src['OnMissingTranslation'])
    w.write_string(src['mTerm_AppName'])

    w.write_string(src['Google_WebServiceURL'])
    w.write_string(src['Google_SpreadsheetKey'])
    w.write_string(src['Google_SpreadsheetName'])
    w.write_string(src['Google_LastUpdatedVersion'])
    w.write_int32(src['GoogleUpdateFrequency'])
    w.write_int32(src['GoogleInEditorCheckFrequency'])
    w.write_int32(src['GoogleUpdateSynchronization'])
    w.write_float(src['GoogleUpdateDelay'])

    assets = src['Assets']
    w.write_int32(len(assets))
    for asset in assets:
        w.write_int32(asset['m_FileID'])
        w.write_int64(asset['m_PathID'])

    return w.bytes()


# ================================================================
# JSON → CSV 변환
# ================================================================