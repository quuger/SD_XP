# SD_XP

[![CI](https://github.com/quuger/SD_XP/actions/workflows/ci.yml/badge.svg)](https://github.com/quuger/SD_XP/actions/workflows/ci.yml)

## Команда
Виноградов Илья
Гребенкин Иван


## Описание приложения 
Консольный peer-to-peer чат, где каждый узел может выступать одновременно как клиент и сервер.

Основные свойства:
* peer-to-peer
* gRPC
* Консольный интерфейс

## Сборка и запуск проекта

* Python версии 3.12
* pip install -r requirements.txt

### Запуск клиента
```bash
python main.py --name "Nickname" --peer localhost:50051
```

### Запуск сервера
```bash
python main.py --name "Nickname"
```


## Запуск тестов
```bash
pytest tests/
```