create policy "users view own scans"
on job_scans for select
using (auth.uid() = (select auth_user_id from users where id = job_scans.user_id));

create policy "users insert own scans"
on job_scans for insert
with check (auth.uid() = (select auth_user_id from users where id = job_scans.user_id));

create policy "users view own reports"
on scam_reports for select
using (auth.uid() = (select auth_user_id from users where id = scam_reports.user_id));
