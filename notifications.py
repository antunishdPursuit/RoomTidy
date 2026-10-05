"""Windows toast delivery with user text encoded as XML data, never shell code."""
import base64
import subprocess
from xml.etree.ElementTree import Element, SubElement, tostring

def notification_script(name,mode):
    toast=Element('toast',{'duration':'long'})
    binding=SubElement(SubElement(toast,'visual'),'binding',{'template':'ToastGeneric'})
    SubElement(binding,'text').text=('DEMO — ' if mode=='demo' else '')+'Room reminder'
    SubElement(binding,'text').text=f'Items have remained on your {name} across recent checks. Take a look?'
    SubElement(toast,'audio',{'silent':'true'})
    encoded=base64.b64encode(tostring(toast,encoding='utf-8')).decode('ascii')
    return '''$ErrorActionPreference='Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null
$xml=New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(''' + "'"+encoded+"'" + ''')))
$toast=[Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('RoomTidy').Show($toast)
'''

def send_notification(name,mode='live'):
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',notification_script(name,mode)],capture_output=True,text=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise RuntimeError((result.stderr or 'Windows rejected the toast.')[:300])
