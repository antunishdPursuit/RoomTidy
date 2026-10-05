import sys,base64
from pathlib import Path
from xml.etree.ElementTree import fromstring
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from notifications import notification_script

def test_name_is_data_not_powershell():
    name='desk $example <books> "quote"'
    script=notification_script(name,'demo')
    assert name not in script
    encoded=script.split("FromBase64String('")[1].split("')")[0]
    xml=fromstring(base64.b64decode(encoded))
    assert name in xml.find('visual/binding').findall('text')[1].text
