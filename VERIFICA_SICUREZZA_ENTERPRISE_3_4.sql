-- RV Manager Enterprise 3.4
-- Query diagnostiche: non eliminano e non modificano dati.

select
    schemaname,
    tablename,
    rowsecurity
from pg_tables
where schemaname = 'public'
  and tablename in (
    'employees',
    'employee_accounts',
    'timesheets',
    'clock_entries',
    'payslips',
    'employee_documents',
    'audit_events'
  )
order by tablename;

select
    schemaname,
    tablename,
    policyname,
    roles,
    cmd,
    qual,
    with_check
from pg_policies
where schemaname in ('public', 'storage')
order by schemaname, tablename, policyname;

select
    id,
    name,
    public
from storage.buckets
where id in ('payslips', 'employee-documents');
