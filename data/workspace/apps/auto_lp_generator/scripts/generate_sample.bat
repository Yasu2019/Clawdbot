@echo off
set PORT=8010
if not "%AUTO_LP_PORT%"=="" set PORT=%AUTO_LP_PORT%
curl -X POST http://127.0.0.1:%PORT%/api/generate ^
-H "Content-Type: application/json" ^
-d "{\"title\":\"品質保証ダッシュボード\",\"subtitle\":\"顧客・監査員向けに品質状況を説明するLP\",\"theme\":\"quality_dashboard\",\"target\":\"製造業の品質責任者\",\"tone\":\"工業的、信頼感、ブルー基調\",\"sections\":[\"KPIサマリー\",\"工程フロー\",\"不良率の推移\",\"是正処置フロー\",\"問い合わせ\"],\"notes\":\"サンプル生成\"}"
echo.
pause
