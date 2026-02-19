# Script de inicialização do projeto Andreja
# Execute: .\start.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Andreja - Agente Técnico de Elevadores" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check .env
if (-not (Test-Path ".env")) {
    Write-Host "ERRO: Arquivo .env não encontrado!" -ForegroundColor Red
    Write-Host "Copie .env.example para .env e configure sua GEMINI_API_KEY" -ForegroundColor Yellow
    exit 1
}

$envContent = Get-Content ".env" -Raw
if ($envContent -match "your_gemini_api_key_here") {
    Write-Host "AVISO: Configure sua GEMINI_API_KEY no arquivo .env antes de continuar!" -ForegroundColor Yellow
    Write-Host "Editando .env..." -ForegroundColor Yellow
}

# Check Docker
try {
    docker version | Out-Null
    Write-Host "Docker encontrado." -ForegroundColor Green
} catch {
    Write-Host "ERRO: Docker nao encontrado. Instale o Docker Desktop primeiro." -ForegroundColor Red
    exit 1
}

# Build and start
Write-Host ""
Write-Host "Iniciando containers..." -ForegroundColor Cyan
docker-compose up --build -d

Write-Host ""
Write-Host "Aguardando servicos..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Sistema iniciado!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend API:  http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:     http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Frontend:     http://localhost:3000" -ForegroundColor White
Write-Host "  Qdrant UI:    http://localhost:6333/dashboard" -ForegroundColor White
Write-Host ""
Write-Host "  Login admin:  admin@andreja.com / admin123" -ForegroundColor Yellow
Write-Host ""
Write-Host "Para parar: docker-compose down" -ForegroundColor Gray
