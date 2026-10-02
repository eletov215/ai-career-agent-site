from datetime import date
import pytest
from domain.reminders import ReminderError
from services.reminders import ReminderService

class Repo:
    def __init__(self): self.p=None; self.r=None
    def get_preference(self,u): return self.p or {'in_app_reminders_enabled':False,'revision':0}
    def set_preference(self,u,e,x,now):
        rev=self.p['revision'] if self.p else 0
        if x != rev: raise ReminderError('stale_write')
        if self.p and self.p['in_app_reminders_enabled']==e:return self.p
        self.p={'in_app_reminders_enabled':e,'revision':rev+1};return self.p
    def list(self,u): return list(self.r or [])
    def save(self,u,s,d,x,now):
        current=(self.r or [None])[0]; rev=current['revision'] if current else 0
        if x != rev: raise ReminderError('stale_write')
        if current and current['due_date']==d.isoformat(): return current
        row={'id':'r','saved_vacancy_id':s,'due_date':d.isoformat(),'revision':rev+1};self.r=[row];return row
    def delete(self,u,s,x):
        if not self.r or self.r[0]['revision'] != x: raise ReminderError('stale_write')
        self.r=[]

def test_default_opt_in_conflicts_and_persistence():
    s=ReminderService(Repo()); assert s.preference('u')['in_app_reminders_enabled'] is False
    assert s.set_preference('u','1','0',now=1)['revision']==1
    with pytest.raises(ReminderError,match='stale_write'): s.set_preference('u','0','0',now=2)
    assert s.set_preference('u','0','1',now=3)['in_app_reminders_enabled'] is False

def test_date_crud_noop_conflict_order_and_labels():
    s=ReminderService(Repo()); row=s.save('u','s','2026-10-02','0',now=1)
    assert s.save('u','s','2026-10-02','1',now=2)['revision']==1
    with pytest.raises(ReminderError,match='stale_write'): s.save('u','s','2026-10-03','0',now=2)
    row=s.save('u','s','2026-10-03','1',now=3); assert s.list('u',date(2026,10,3))[0]['label']=='Сегодня'
    s.delete('u','s',row['revision']); assert s.list('u')==[]
