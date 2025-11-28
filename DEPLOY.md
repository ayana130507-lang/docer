# Deploy & Publish Guide

Этот файл содержит пошаговые команды для локальной сборки, загрузки образа в Docker Hub / GHCR и быстрых инструкций по развёртыванию в облаке (Cloud Run, Render, Fly.io). Также описаны настройки GitHub Actions для автоматической сборки/публикации и пример автоматического деплоя в Cloud Run.

## Локальная сборка и запуск (PowerShell)

```powershell
# Собрать образ локально
docker build -t docer:local .

# Запустить контейнер (порт 5000 -> 5000)
docker run -p 5000:5000 docer:local

# Проверка
Invoke-RestMethod http://localhost:5000
```

## Push to Docker Hub (manual)

1. Создайте репозиторий на https://hub.docker.com/
2. Выполните вход:

```powershell
docker login
```

3. Тэг и push:

```powershell
docker tag docer:local YOUR_DOCKERHUB_USERNAME/docer:latest
docker push YOUR_DOCKERHUB_USERNAME/docer:latest
```

## Push to GitHub Container Registry (GHCR) — recommended for GitHub projects

Вы можете запушить вручную или настроить автоматическую публикацию через GitHub Actions.

### Ручной push (локально)

1. (Опционально) создайте PAT с правами `write:packages` и `read:packages` в GitHub.
2. Войдите в GHCR:

```powershell
echo "YOUR_GHCR_PAT" | docker login ghcr.io -u YOUR_GH_USERNAME --password-stdin
```

3. Тэг и push:

```powershell
docker tag docer:local ghcr.io/YOUR_GH_USERNAME/docer:latest
docker push ghcr.io/YOUR_GH_USERNAME/docer:latest
```

### Рекомендуемый — автоматический через GitHub Actions

В репозитории уже есть workflow: `.github/workflows/publish-image.yml`.
Этот workflow использует `GITHUB_TOKEN` чтобы залогиниться в `ghcr.io` и опционально может пушить в Docker Hub при наличии секретов `DOCKERHUB_USERNAME` и `DOCKERHUB_TOKEN`.

Как настроить (быстро):
1. В GitHub → Your repo → Settings → Secrets and variables → Actions нажмите `New repository secret`.
2. Если хотите пушить на Docker Hub тоже, добавьте `DOCKERHUB_USERNAME` и `DOCKERHUB_TOKEN` (Docker Hub access token).
3. Отправьте изменения в `main` — workflow автоматически соберёт и отправит образы в `ghcr.io/<owner>/<repo>:latest` (и в Docker Hub, если заданы секреты).

## Развёртывание контейнера в облаке (выберите один)

Ниже — быстрые инструкции для популярных провайдеров и пример автодеплоя в Cloud Run.

### Вариант A — Google Cloud Run (самый простой)

1. Создайте проект в Google Cloud.
2. Установите Google Cloud CLI и авторизуйтесь: `gcloud auth login`.
3. Включите API: `gcloud services enable run.googleapis.com`

Ручный деплой (пример):

```powershell
gcloud run deploy docer-app `
  --image=ghcr.io/YOUR_GH_USERNAME/docer:latest `
  --platform=managed `
  --region=europe-west1 `
  --allow-unauthenticated `
  --min-instances=1 `
  --max-instances=5
```

Cloud Run автоматически масштабирует контейнеры по входящим запросам. Укажите `--min-instances` и `--max-instances` для контроля.

### Автоматический деплой в Cloud Run из GitHub Actions (пример)

Если хотите автоматизировать: добавьте секреты в репозиторий:
- `GCP_PROJECT` — ваш GCP project id
- `GCP_SA_KEY` — JSON ключ сервисного аккаунта (создайте сервисный аккаунт с ролями Cloud Run Admin и Service Account User)

Создайте файл `.github/workflows/deploy-cloudrun.yml` со следующим содержимым:

```yaml
name: Build, Push and Deploy to Cloud Run
on:
  push:
    branches: [ main ]

jobs:
  build-push-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v2
      - name: Build and push to GHCR
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/${{ github.event.repository.name }}:latest

      - name: Setup gcloud
        uses: google-github-actions/setup-gcloud@v1
        with:
          project_id: ${{ secrets.GCP_PROJECT }}
          service_account_key: ${{ secrets.GCP_SA_KEY }}

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy docer-app \
            --image=ghcr.io/${{ github.repository_owner }}/${{ github.event.repository.name }}:latest \
            --platform=managed --region=europe-west1 --allow-unauthenticated --min-instances=1 --max-instances=5
```

После пуша в `main` workflow соберёт, запушит образ и задеплоит сервис. В Cloud Run вы сможете настроить дополнительные правила автоскейлинга (CPU, concurrency и т.д.).

### Вариант B — AWS ECS + Fargate

Коротко:
1. Создайте кластер Fargate.
2. Создайте task definition, укажите контейнерный образ из Docker Hub или GHCR и порт (5000).
3. Запустите сервис (min 1 task).
4. Настройте Application Auto Scaling и балансировщик (ALB) для доступа извне.

### Вариант C — Azure Container Apps

1. Создайте ресурсную группу и среду Container Apps.
2. Разверните приложение, укажите образ, порт и публичный доступ.
3. Настройте авто-масштабирование по CPU/RPS.

### Вариант D — Render / Fly.io

Render:
1. Создайте Web Service и укажите Docker Hub / GHCR образ.
2. В настройках включите авто scale и укажите min/max.

Fly.io:
```powershell
# Установите flyctl и войдите
fly launch
fly deploy --image ghcr.io/YOUR_GH_USERNAME/docer:latest
fly autoscale set min=1 max=3
```

## Настройка авто-масштабирования — требования студента

1. Включите автоматическое увеличение количества контейнеров при росте нагрузки.
2. Покажите настройки авто-масштабирования: по CPU (например, >60%), по RPS (если доступно), по памяти.

Примеры:
- Cloud Run: `--min-instances` / `--max-instances` (например max-instances: 5, min-instances: 0)
- AWS ECS / Application Auto Scaling: min=1, max=3, target CPU = 50%

---

Если хотите, могу сделать шаги за вас:
- Настроить GitHub Actions для автоматической сборки и публикации в GHCR (и Docker Hub);
- Создать workflow для автоматического деплоя в Cloud Run (потребуются GCP секреты);
- Или показать пошагово команды для локального пуша и ручного деплоя.

Скажите, хотите ли вы использовать **GHCR (рекомендуется)** или **Docker Hub**, и нужно ли автоматизировать деплой в **Cloud Run** (я тогда подготовлю workflow и инструкции по созданию сервисного аккаунта и секретов).
# Deploy & Publish Guide

Этот файл содержит пошаговые команды для локальной сборки, загрузки образа в Docker Hub / GHCR и быстрых инструкций по развёртыванию в облаке (Cloud Run, Render, Fly.io).

**Локальная сборка и запуск (PowerShell)**

```powershell
# Собрать образ локально
docker build -t docer:local .

# Запустить контейнер (порт 5000 -> 5000)
docker run -p 5000:5000 docer:local

# Проверка
Invoke-RestMethod http://localhost:5000
```

**Push to Docker Hub**

```powershell
docker login
docker tag docer:local YOUR_DOCKERHUB_USERNAME/docer:latest
docker push YOUR_DOCKERHUB_USERNAME/docer:latest
```

**Push to GitHub Container Registry (GHCR)**

Create a Personal Access Token (PAT) with `write:packages` and `read:packages`.

```powershell
echo "GHCR_TOKEN" | docker login ghcr.io -u YOUR_GH_USERNAME --password-stdin
docker tag docer:local ghcr.io/YOUR_GH_USERNAME/docer:latest
docker push ghcr.io/YOUR_GH_USERNAME/docer:latest
```

**Deploy to Google Cloud Run**

1. Установите и авторизуйте `gcloud`.
2. Включите API: `gcloud services enable run.googleapis.com`

```powershell
gcloud run deploy docer-app `
  --image=ghcr.io/YOUR_GH_USERNAME/docer:latest `
  --platform=managed `
  --region=europe-west1 `
  --allow-unauthenticated `
  --min-instances=1 `
  --max-instances=5
```

Cloud Run авто-масштабирует контейнеры автоматически по входящим запросам. Укажите `--min-instances` и `--max-instances` для контроля.

**Render**

1. Создайте Web Service в Render, укажите Docker Hub образ.
2. В настройках включите авто scale и укажите min/max instances.

**Fly.io (example)**

```powershell
# Установите flyctl и войдите
fly launch
# В build укажите Docker image или подключите репозиторий
fly deploy --image ghcr.io/YOUR_GH_USERNAME/docer:latest
fly autoscale set min=1 max=3
```

---

Если хотите, могу: помочь создать репозиторий на Docker Hub/GitHub, настроить секреты в GitHub Actions и выполнить пуш/деплой (вам потребуется предоставить токены через безопасный канал или настроить их в GitHub).
