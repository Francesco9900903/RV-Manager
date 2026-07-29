-- RV Manager Enterprise 3.6
-- Vista diagnostica RLS. Non modifica policy esistenti.

create or replace view public.rls_diagnostic as
select
    c.relname::text as table_name,
    c.relrowsecurity as rls_enabled,
    count(p.policyname)::int as policy_count
from pg_class c
join pg_namespace n
  on n.oid = c.relnamespace
left join pg_policies p
  on p.schemaname = n.nspname
 and p.tablename = c.relname
where n.nspname = 'public'
  and c.relkind = 'r'
  and c.relname in (
    'employee_accounts',
    'timesheets',
    'clock_entries',
    'payslips',
    'employee_documents',
    'employee_notifications'
  )
group by c.relname, c.relrowsecurity;

revoke all on public.rls_diagnostic from public;
grant select on public.rls_diagnostic to service_role;
