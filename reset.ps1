# ==============================================================================
# TicketWar – Quick Data Reset Script
# Menghapus seluruh pesanan, tiket, dan mereset kuota kembali ke 500 dalam 1 detik.
# ==============================================================================

param (
    [int]$Cat1Quota = 500,
    [int]$VipQuota  = 20
)

Write-Host "🔄 Mereset Database PostgreSQL..." -ForegroundColor Cyan
docker exec ticketwar_db psql -U ticketwar -d ticketwar_db -c @"
TRUNCATE tickets, orders, audit_logs CASCADE;
UPDATE ticket_categories SET total_quota = $Cat1Quota, available_quota = $Cat1Quota WHERE id = 1;
UPDATE ticket_categories SET total_quota = $VipQuota, available_quota = $VipQuota WHERE id = 2;
"@ | Out-Null

Write-Host "🔄 Mengosongkan Cache & Kuota Redis..." -ForegroundColor Cyan
docker exec ticketwar_redis redis-cli FLUSHALL | Out-Null
docker exec ticketwar_redis redis-cli SET quota:1 $Cat1Quota | Out-Null
docker exec ticketwar_redis redis-cli SET quota:2 $VipQuota | Out-Null

Write-Host "✅ RESET SELESAI!" -ForegroundColor Green
Write-Host "-------------------------------------------"
Write-Host "CAT 1 Kuota : $Cat1Quota tiket"
Write-Host "VIP Kuota   : $VipQuota tiket"
Write-Host "Orders      : 0 pesanan (bersih)"
Write-Host "Tickets     : 0 tiket (bersih)"
Write-Host "-------------------------------------------"
Write-Host "🚀 Siap untuk dilakukan pengujian beban kembali!" -ForegroundColor Yellow
