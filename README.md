# Tic-Tac-Toe RL

[Русский](#русский) | [English](#english)

## Русский

Я сделал приложение по архитектурной идее из шахматного архива: правила отдельно, агент отдельно, интерфейс отдельно. Здесь есть классические и бесконечные крестики-нолики, три режима участников и настоящее обучение через self-play. Поле чёрное, линии белые, X красный, O синий. Для графиков я использовал Canvas, поэтому NumPy, Matplotlib, PyTorch и интернет при работе не нужны.

### Быстрый запуск

1. Полностью распакуйте ZIP в обычную папку с правом записи.
2. Нужен Python 3.9+ с Tkinter и графический рабочий стол. Рекомендуемая нижняя версия Tcl/Tk - 8.6. Откройте терминал в папке `tic-tac-toe`.
3. Запустите:

```bash
python play.py
```

После этого все обычные действия доступны кнопками. Ничего устанавливать через pip не требуется, `requirements.txt` оставлен для явного описания зависимостей. ZIP содержит исходники и обученные модели, но не сам интерпретатор Python.

| ОС | Подготовка |
| --- | --- |
| Windows | Установите Python с компонентом Tcl/Tk и добавлением Python в PATH. Если команда называется `py`, можно использовать `py play.py`. |
| macOS | Нужна сборка Python с рабочим Tkinter, например установленная с python.org. Если доступна только команда `python3`, используйте `python3 play.py`. |
| Linux | В Debian/Ubuntu при отсутствии Tkinter установите системный пакет `sudo apt install python3-tk`. В других дистрибутивах нужен аналогичный пакет для выбранного Python. Запускайте из графического сеанса. |

Приложение не рассчитано на сервер без экрана, браузерную тетрадку и мобильный Python. Если папка проекта защищена от записи, перенесите её в свою рабочую папку. Игровые пути считаются от файлов проекта, а не от текущей папки терминала.

### Управление

| Элемент | Что делает |
| --- | --- |
| Правила | Классика или Бесконечные |
| Участники | Человек vs Машина, Машина vs Машина, Человек vs Человек |
| Ваша сторона | X или O в игре против машины; X всегда начинает |
| Новая игра | Применяет выбранные правила, участников и сторону |
| Перезапустить раунд | Начинает заново с текущими активными настройками |
| Пауза / Продолжить | Останавливает или продолжает ходы; на паузе человек тоже не ходит |
| Один ход машины | Ставит игру на паузу и делает один ход, если очередь машины |
| Задержка машины | Меняет скорость наблюдения, от 100 до 2000 мс |
| Загрузить X / O | Даёт каждой стороне свой совместимый файл `.ttq.gz` |
| Сохранить X / O | Экспортирует выбранную модель |
| Статистика RL | Показывает числа и четыре графика; переключатель X/O выбирает модель |
| Оценить за 500 партий | Проверяет выбранную модель против случайного игрока |
| Обучить / дообучить | Открывает отдельное окно обучения, взяв копию текущей модели X |
| Сохранить CSV / SVG | Экспортирует историю обучения и графики |
| Сбросить счёт | Обнуляет счёт завершённых партий за текущий сеанс |
| Как играть / Выход | Открывает правила или закрывает программу |

Для хода нажмите на пустую клетку. Изменения правил, участников и стороны применяются кнопкой Новая игра. В режиме двух людей оба игрока используют одну мышь. Счёт относится ко всему сеансу и включает оба варианта правил. При повторном запуске он начинается с нуля. Язык и активные настройки сохраняются в `data/settings.json`. Загруженные вручную модели между запусками не запоминаются: их можно снова открыть кнопками. По умолчанию загружаются модели из `models/`.

В исходном задании Человек vs Машина встречался два раза. Я трактовал третий вариант как Человек vs Человек, чтобы получить три разных режима.

### Правила Infinite

У каждой стороны одновременно может быть максимум три символа. Я реализовал ход так:

1. Игрок выбирает клетку, которая пуста до начала хода.
2. Новый символ добавляется в конец очереди этой стороны.
3. Если символов стало четыре, самый старый удаляется.
4. После удаления проверяется линия из трёх.

На клетку со своим самым старым символом ходить нельзя: во время выбора она ещё занята. Номера 1, 2, 3 показывают возраст, где 1 - самый старый. Когда символов три, пунктир вокруг старого символа напоминает о его будущем исчезновении. Это касается обеих сторон. Линия, которая существовала только до удаления старого символа, не считается победой.

В Infinite возможны циклы. Поэтому в интерфейсе после 120 отдельных ходов без победы объявляется ничья. Повтор позиции сам по себе игру не останавливает. Победа на 120-м ходу имеет приоритет над лимитом. В классике ничья наступает при заполнении поля без победной линии.

### Обучение и дообучение

Можно открыть окно кнопкой в игре или отдельно:

```bash
python train.py
```

Всё окно обучения и все его графики всегда на английском, независимо от языка игры. Открытие окна из игры ставит партию на паузу. После обучения вернитесь в игру и нажмите Продолжить или Новая игра.

- **New model** создаёт пустую $Q-таблицу$ для выбранных Rules и Seed. Это сброс обучения.
- **Load checkpoint** загружает свою модель, её seed, историю и состояние обучения.
- **Additional episodes** задаёт, сколько партий добавить к уже пройденным.
- **Start / continue** начинает или продолжает обучение. Для смены Rules сначала нажмите New model. Поле Seed применяется только при New model.
- **Pause / Resume** приостанавливает и продолжает работу на границе партий.
- **Stop & save** завершает текущую партию и сохраняет прогресс.
- **Save model as...** позволяет выбрать имя и место сохранения.
- **Export CSV / Export charts (SVG)** сохраняет данные и векторные графики.
- **Close** во время обучения сначала останавливает его и сохраняет прогресс.

Рабочие модели и CSV появляются в `data/models/`. Программа сохраняет модель каждые 500 партий, в конце и при штатной остановке. При жёстком завершении процесса останется последний успешно записанный checkpoint. Сохранение атомарное: сначала временный файл, потом замена целевого. Комплектные модели из `models/` автоматически не меняются.

Если окно открыто из игры, после окончания или Stop & save обученная модель назначается обеим сторонам своего варианта правил. Для сравнения разных версий сохраните их под разными именами и загрузите отдельно в X и O. Обучение идёт в фоновом потоке на собственной копии агента; Tkinter обновляется только главным потоком.

### Какой RL-подход я выбрал

В шахматном примере используется DQN. Для поля 3x3 я выбрал табличный $Q-learning$: здесь таблица компактна, её проще отлаживать и продолжать без тяжёлых зависимостей. Это обучаемая модель ценности действий, а не нейросеть. Встроенного $\texttt{minimax}$, подсказок о выигрышных ходах и подмены модели эвристиками нет.

Состояние записывается относительно того, кто ходит: свои символы и символы соперника. В классике достаточно девяти клеток. В Infinite я храню две упорядоченные очереди клеток. По ним можно восстановить поле и точно понять, что исчезнет. Повороты и отражения объединяются через восемь симметрий квадрата D4. Индекс действия переводится в ту же систему координат. Нелегальные клетки исключаются и при выборе действия, и при вычислении TD-цели.

Один агент играет обеими сторонами. Поэтому ценность следующего состояния принадлежит сопернику и в цели нужен минус:

$$
y = r \quad \text{для настоящего терминального шага}
$$
$$
y = r - \gamma \cdot \max_{\text{legal}} Q(s_{\text{next}}, a_{\text{next}}) \quad \text{иначе}
$$
$$
Q(s, a) \leftarrow Q(s, a) + \alpha \cdot \bigl( y - Q(s, a) \bigr)
$$

Награда за выигрышный ход равна +1, за остальные ходы 0. Проигрыш получает отрицательную оценку через отрицание ценности соперника. Штрафа за ход нет. Я использовал $\alpha=0.25$ , $\gamma=0.97$, $\epsilon-greedy$ и случайный выбор между равными лучшими действиями. $\epsilon$ линейно идёт от 0.9 до 0.05: за 40 000 партий в классике и 100 000 в Infinite. В обычной игре $\epsilon=0$; случайность остаётся только при равных оценках. Новые, неизвестные состояния имеют нулевые $Q$. 

Лимит Infinite считается **truncation** продолжающейся игры. При нём интерфейс показывает ничью, но обучение сохраняет $\texttt{bootstrap}$ из следующего состояния. Так я не смешиваю ограничение времени с настоящим терминальным исходом и не добавляю номер хода в ключ таблицы. Настоящая победа и заполнение поля в классике обрабатываются как **termination**, где $\texttt{bootstrap}=0$.

Для табличного варианта я не использовал replay buffer, target network и Adam. Их состояние здесь просто не существует. В checkpoint сохраняются таблица, параметры, счётчики, история, результаты self-play и RNG. Поэтому продолжение с границы партии восстанавливает ту же последовательность учебных действий. Время выполнения может отличаться. Графики ошибок усредняются по новым шагам текущего интервала логирования; после ручной остановки окно усреднения начинается заново. Это не меняет $Q-обновления$.

### Как читать статистику

- **TD MSE** - средний квадрат $(y-Q(s,a))$ до обновления таблицы. Это не loss нейросети.
- **Exploration** - текущее значение $\epsilon$ при обучении.
- **Mean game length** - среднее число отдельных ходов в self-play за интервал.
- **Evaluation vs random** - доли побед, ничьих и поражений на 200 контрольных партиях при каждой записи истории. Стороны чередуются, seed оценки 1042.
- Отдельная кнопка оценки в статистике использует 500 партий. `Score` учитывает ничью как половину очка, `Win` считает только победы.

RNG оценки независим от RNG обучения. Для нового обучения одинаковый seed даёт одинаковую учебную траекторию. Оценка против случайного полезна для сравнения, но сама по себе не доказывает оптимальность и не измеряет силу против человека. Падение TD MSE тоже не является таким доказательством.

### Комплектные модели

Я обучил обе модели с seed 42. Фактическая проверка на 2000 партиях против случайного соперника, стороны по очереди, seed 1042:

| Модель | Партий обучения | Состояний | Победы | Ничьи | Поражения |
| --- | --- | --- | --- | --- | --- |
| Classic | 60 000 | 627 | 1734 | 266 | 0 |
| Infinite | 100 000 | 8344 | 2000 | 0 | 0 |

Для сравнения, необученный агент при том же протоколе получил 851/272/877 в классике и 1018/0/982 в Infinite. Полные числа, версия Python и условия прогона лежат в `models/evaluation.json`; исходные кривые лежат рядом в CSV. Это результаты конкретного seed и соперника, а не обещание результата каждой игры.

### Структура и проверки

```text
tic-tac-toe/
  localization/       en.tsv, ru.tsv, загрузчик словарей
  gui/                окно игры, статистика, обучение, Canvas-графики
  src/                environment.py, agent.py, training.py
  models/             две готовые модели, CSV, evaluation.json
  docs/               разбор исходного архива и протокол проверок
  tests/              правила, RL, дообучение, проверка GUI
  play.py             обычный запуск
  train.py            отдельное окно обучения
  README.md
  requirements.txt
  data/               создаётся во время работы
```

На macOS и Windows выполнены проверки ядра и интеграционный тест Tkinter. Linux в этом окружении не запускались. Для них использован тот же переносимый код стандартной библиотеки; требуется рабочая сборка Python с Tkinter.

## English

I kept the architectural idea of the chess archive: separate rules, agent and UI. The app includes Classic and Infinite Tic-Tac-Toe, Human vs Machine, Machine vs Machine and Human vs Human. The duplicate Human vs Machine entry in the request was interpreted as Human vs Human. The board is black, grid white, X red and O blue.

### Run

Extract the entire archive to a writable directory. Use Python 3.9+ with Tkinter, Tcl/Tk 8.6+ and a graphical desktop session. In the `tic-tac-toe` directory run:

```bash
python play.py
```

No pip dependencies are needed. The archive includes source and models, not a Python runtime. On Windows install Python with Tcl/Tk and PATH support; `py play.py` also works when `py` is the available launcher. On macOS use a Python build with working Tkinter. On Linux install the Tkinter system package if needed; Debian/Ubuntu uses `sudo apt install python3-tk`. Use `python3 play.py` if your interpreter is named `python3`. A headless server or browser notebook cannot show the desktop UI.

Paths are relative to the project files, so the current working directory does not affect model discovery. Keep the extracted directory writable for checkpoints and preferences. Network access is not used by the application.

### Controls

- Select rules, players and your side, then press **New game** to apply them. X always starts. Human vs Human uses one mouse.
- **Restart round** repeats the currently active setup. **Pause / Resume** freezes both human and machine moves. **One machine move** pauses and advances one AI turn.
- The delay slider changes observation speed immediately.
- **Load X / O** and **Save X / O** manage separate models, including AI comparisons. A model must match the selected active rules.
- **RL statistics** shows numeric metrics and four charts. Its X/O selector chooses the inspected model. **Evaluate 500 games** measures it against random play. **Export CSV** and **Export charts (SVG)** save data and vector charts.
- **Train / continue** opens the training dashboard using a copy of model X and pauses the match. After training press Resume or New game in the game window.
- **Reset score** clears completed-round totals for this session, across both rule sets. **How to play**, **Close** and **Exit** are available as buttons.
- The language selector changes the game and statistics between Russian and English. Training controls and training charts always remain English.

Language and active setup are saved to `data/settings.json`. The session score resets on launch. Manually loaded models are not remembered across launches; the bundled models are loaded by default. Load your saved model again when needed.

### Infinite rules

Place on a cell that is empty before your move, append the symbol to your queue, remove your oldest symbol if you now have four, then check for a line of three. You cannot place directly on the still occupied oldest cell. A temporary line that disappears after removal does not win. Labels 1 to 3 show oldest to newest; a dotted ring marks the next symbol to disappear when that side has three.

Infinite can cycle, so the UI draws the round after 120 individual moves without a win. A win on move 120 takes priority. Repetition alone does not end a round. Classic draws when the board is full without a winning line.

### Training and resuming

Use the in-game button or open a standalone dashboard:

```bash
python train.py
```

**New model** resets the table using the chosen Rules and Seed. **Load checkpoint** restores an existing model. **Additional episodes** means episodes to add, not a lifetime target. **Start / continue** resumes the current model. To change the rules press New model first; Seed only applies to New model.

**Pause / Resume** takes effect at episode boundaries. **Stop & save** finishes the current episode and saves. Closing the training window or application also requests a graceful stop and save. **Save model as...**, **Export CSV** and **Export charts (SVG)** let you choose output files after the worker stops.

Working checkpoints and CSV files go into `data/models/`. Models are saved every 500 episodes and at the end or a graceful stop. Abrupt termination retains the last completed checkpoint. Writes use temporary files and atomic replacement. Bundled models are not overwritten automatically. When training was opened from the game, its resulting model is assigned to both sides of that rule set. Save versions under separate names and load X and O separately to compare them.

### RL choices

I used tabular Q-learning rather than the archive's DQN because this state space is small. There is no neural network, hidden minimax search or tactical override. The model learns action values from self-play, with one agent controlling both sides. State is player-relative. Classic uses cell contents; Infinite uses ordered queues for both sides, preserving symbol age. Eight D4 symmetries share table entries, and actions are transformed consistently. Only legal actions are used both in selection and in the TD target.

$$
y = r \quad \text{at genuine termination}
$$
$$
y = r - \gamma \cdot \max_{\text{legal}} Q(s_{\text{next}}, a_{\text{next}}) \quad \text{otherwise}
$$
$$
Q(s, a) \leftarrow Q(s, a) + \alpha \cdot \bigl( y - Q(s, a) \bigr)
$$

The minus sign matters: the next state's values belong to the opponent. A winning move gets +1; other moves get 0. Negative loss values propagate through the negamax target. I used $\alpha=0.25$, $\gamma=0.97$ and $\epsilon-greedy$ exploration. $\epsilon$ falls linearly from 0.9 to 0.05 over 40,000 Classic or 100,000 Infinite episodes. Ordinary matches use $\epsilon$ 0, with random tie breaking. Unknown states start at 0.

The Infinite time limit truncates a continuing game, so learning still $\texttt{bootstraps}$ at that boundary even though the UI reports a draw. Genuine wins and Classic full-board draws terminate, with no $\texttt{bootstrap}$. This avoids putting a remaining-time counter into the continuing-game state.

The table does not require a replay buffer, target network or Adam. Checkpoints store $Q$ values, parameters, counters, self-play outcomes, history and RNG state as gzip-compressed JSON, without pickle. Resuming at an episode boundary restores the same learning trajectory; elapsed times can differ. Metric averaging restarts for each training call, which does not change $Q$ updates.

### Metrics and bundled results

TD MSE is the mean squared TD error before updating $Q$. Game length counts individual moves. History evaluates 200 games against random at each logged point; the statistics button uses 500. Evaluation alternates sides and uses seed 1042, with an RNG independent of training. Win rate counts wins only; score gives draws half a point. Neither a low TD error nor success against random proves optimal play.

Both bundled models were trained with seed 42. Evaluation on 2,000 games:

| Model | Training episodes | States | Wins | Draws | Losses |
| --- | --- | --- | --- | --- | --- |
| Classic | 60,000 | 627 | 1734 | 266 | 0 |
| Infinite | 100,000 | 8344 | 2000 | 0 | 0 |

The untrained baseline scored 851/272/877 in Classic and 1018/0/982 in Infinite under the same protocol. Full results and environment metadata are recorded in `models/evaluation.json`; training curves are supplied as CSV. These figures describe one protocol, not a guarantee against humans or stronger opponents.

### Structure and checks

```text
tic-tac-toe/
  localization/       en.tsv, ru.tsv, dictionary loader
  gui/                game window, statistics, training, Canvas plots
  src/                environment.py, agent.py, training.py
  models/             two ready-made models, CSV, evaluation.json
  docs/               source archive analysis and verification protocol
  tests/              rules, RL, fine-tuning, GUI checks
  play.py             standard launch
  train.py            separate training window
  README.md
  requirements.txt
  data/               created at runtime
```

Core tests and a Tkinter integration test were run on macOS and Windows. Linux were not executed in this environment; the code uses portable standard-library APIs.
