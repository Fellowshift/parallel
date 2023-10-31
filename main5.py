from typing import List, Tuple, Callable
import time
from datetime import datetime
from multiprocessing import Process, current_process, Manager
import signal


class ProcessController:
    def __init__(self, max_proc: int = 1):
        self.max_proc = max_proc
        self.interrupted_tasks = Manager().list()  # Используем разделяемый список
        self.processes = []  # Список процессов
        self.tasks_queue = []  # Список задач
        self.completed_tasks = 0  # Перечень успешно стартовавших задач

    def set_max_proc(self, n: int):
        self.max_proc = n  # Max параллельных процессов

    def timeout_handler(self, signum, frame):
        # Реализация хендлера для прерывания процесса
        raise TimeoutError

    def run_task(self, task: Callable, args: Tuple, max_exec_time: int):
        # Запуск задачи
        start_time = time.time()
        process_id = current_process().pid
        print(f'Задание {task.__name__}{args[0]} запущено. '
              f'Текущее время {start_time}, ID процесса {process_id}')
        try:
            signal.signal(signal.SIGALRM, self.timeout_handler)
            signal.alarm(max_exec_time)  # Установка обработчика на время
            task(*args)  # Выполняем задачу
            execution_time = time.time() - start_time
            if execution_time > max_exec_time:
                raise TimeoutError
            print(f'Задание {task.__name__}{args[0]} завершено. '
                  f'Время выполнения {execution_time},'
                  f' ID процесса {process_id}')
        except TimeoutError:
            print(f'\nЗадание {task.__name__}{args[0]} превысило '
                  f'время выполнения. Время прерывания {datetime.now()}, '
                  f'Время работы программы {time.time() - start_time}, '
                  f'ID процесса {process_id}\n')
            # Добавляем прерванное задание в общий список interrupted_tasks
            self.interrupted_tasks.append((task, args))

    def start(self, tasks: List[Tuple[Callable, Tuple]], max_exec_time: int):
        # Запуск всех задач
        self.tasks_queue = tasks  # Заполняем список задач
        while len(self.tasks_queue) > 0 or len(self.processes) > 0:
            self.processes = [p for p in self.processes if p.is_alive()]
            while (len(self.processes) < self.max_proc
                   and len(self.tasks_queue) > 0):
                task, args = self.tasks_queue.pop(0)
                process = Process(target=self.run_task,
                                  args=(task, args, max_exec_time))
                self.processes.append(process)
                process.start()
                self.completed_tasks += 1
            time.sleep(0.1)  # Пауза для избежания бесконечного цикла

    def wait(self):
        # Ожидание завершения процессов
        for process in self.processes:
            process.join()

    def interrupted_count(self) -> int:
        # Получение количества прерванных задач
        return len(self.interrupted_tasks)

    def wait_count(self) -> int:
        # Получение количества задач, ожидающих запуска
        return len(self.tasks_queue)

    def completed_count(self) -> int:
        # Получение количества успешных задач
        return (self.completed_tasks - self.interrupted_count()
                - self.wait_count() - self.alive_count())

    def alive_count(self) -> int:
        # Получение количества работающих задач
        return len(self.processes)


"""Пример использования"""


def test_function(n):
    time.sleep(n)


# Создаем экземпляр нашего ProcessController
pc = ProcessController()
pc.set_max_proc(2)
max_exec_time = 4  # Время ожидания в секундах

# Запускаем набор заданий с таймаутом max_exec_time
tasks = [(test_function, (n,)) for n in [2, 5, 3, 7, 1]]
pc.start(tasks, max_exec_time)

print(f'Количество заданий выполняемых в данный момент: {pc.alive_count()}')
print(f'Количество заданий ждущих запуск: {pc.wait_count()}')

pc.wait()

print(f'Количество прерванных заданий: {pc.interrupted_count()}')
print(f'Количество успешных заданий: {pc.completed_count()}')
