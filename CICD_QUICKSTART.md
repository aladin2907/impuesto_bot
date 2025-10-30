# CI/CD Quick Start 🚀

## Что настроили:

✅ **GitHub Actions** - build на GitHub серверах (не убивает твой сервер!)  
✅ **GitHub Container Registry** - хранение Docker образов (бесплатно)  
✅ **Auto-deploy** - push в main = автодеплой на production  

## Что нужно сделать СЕЙЧАС:

### 1. Включи GitHub Container Registry (30 сек)

```
GitHub repo → Settings → Actions → General → Workflow permissions
→ Select: "Read and write permissions" → Save
```

### 2. Добавь 3 секрета (2 мин)

```
GitHub repo → Settings → Secrets and variables → Actions → New repository secret
```

**Секрет 1:** `SSH_HOST`  
Value: `63.180.170.54`

**Секрет 2:** `SSH_USER`  
Value: `ubuntu`

**Секрет 3:** `SSH_PRIVATE_KEY`  
Value: Весь контент файла (включая BEGIN/END):
```bash
cat /Users/macbook/credy/myown/AWS/MyKeyPairN8Nserver.pem
```

### 3. Сделай первый deploy (1 мин)

```bash
cd /Users/macbook/PetProjects/impuesto_bot
git add .
git commit -m "feat: setup CI/CD pipeline"
git push origin main
```

### 4. Смотри магию ✨

```
GitHub repo → Actions tab
→ Видишь "Build and Deploy" workflow
→ Жди ~5-7 минут
→ PROFIT! 🎉
```

## Проверка после деплоя:

```bash
# Проверь API
curl http://63.180.170.54/health

# Проверь контейнеры
ssh -i /Users/macbook/credy/myown/AWS/MyKeyPairN8Nserver.pem ubuntu@63.180.170.54 "docker ps"
```

## Как это работает:

1. **Push в main** → GitHub Actions триггерится
2. **Build** происходит на серверах GitHub (НЕ твой сервер!)
3. **Push** образа в `ghcr.io/aladin2907/impuesto_bot:latest`
4. **SSH** в твой сервер
5. **Pull** нового образа
6. **Restart** контейнеров
7. **Done!** 🚀

## Преимущества:

- ✅ **0 нагрузки** на твой 1GB RAM сервер
- ✅ **Быстро** - только pull образа, не build
- ✅ **Автоматически** - просто push code
- ✅ **Бесплатно** - GitHub Actions free для public repos
- ✅ **Rollback** - можешь откатиться на любую версию

## Troubleshooting:

**Workflow fails на build?**
→ Check Settings → Actions → Permissions

**Workflow fails на deploy?**
→ Check Secrets (SSH_HOST, SSH_USER, SSH_PRIVATE_KEY)

**Образ не public?**
→ GitHub repo → Packages → impuesto_bot → Package settings → Change visibility to Public

## Next deploys:

Просто:
```bash
git add .
git commit -m "your changes"
git push origin main
```

Всё остальное - автоматом! 🎉

