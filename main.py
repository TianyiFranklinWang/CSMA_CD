import asyncio
import logging
import os
import random
import time


class Bus:
    data = [None for _ in range(5)]
    voltage_flag = 0


class Client:
    def __init__(self, name):
        self._max_collision_endure = 16

        self.name = name

        self.data = str(random.randrange(10000, 99999))

        self.success_timer = 0
        self.fail_timer = 0
        self.global_timer = 0

        self.collision_timer = 16

        self.send_ok = 0

    async def report(self):
        message = f"\ndata:               {self.data}\n" \
                  f"global timer:       {self.global_timer}\n" \
                  f"  success timer:      {self.success_timer}\n" \
                  f"  fail timer:         {self.fail_timer}\n" \
                  f"collision timer:    {self.collision_timer}\n"
        logging.info(message)

    def reset_all(self):
        self.data = str(random.randrange(10000, 99999))
        self.success_timer = 0
        self.fail_timer = 0
        self.global_timer = 0
        self.collision_timer = 16

    def reset_collision_timer(self):
        self.collision_timer = 16

    def get_data(self):
        self.data = str(random.randrange(10000, 99999))

    def update_timer_on_success(self):
        self.success_timer += 1
        self.global_timer = self.success_timer + self.fail_timer

    def update_timer_on_failure(self):
        self.fail_timer += 1
        self.global_timer = self.success_timer + self.fail_timer

    async def wait_util_free(self):
        while Bus.voltage_flag != 0:
            await asyncio.sleep(0.0001)

    def get_backoff_time(self, time):
        k = time if time <= 10 else 10
        r = random.randrange(0, 2 ** k - 1)
        return r * 0.00512

    def validate_sending(self):
        Bus.voltage_flag -= 1
        bus_data = ''
        for i in range(len(Bus.data)):
            bus_data += Bus.data[i]

        if bus_data == self.data:
            logging.info(f"{self.name} send success")
            self.update_timer_on_success()
            self.reset_collision_timer()
            self.send_ok = 1
        else:
            self.update_timer_on_failure()
            self.reset_collision_timer()
            logging.info(
                f"{self.name} send failed, bus_data: {bus_data} not correspond to self.data: {self.data}")

    async def send(self):
        start_time = random.randrange(1, 96) / 100000
        await asyncio.sleep(start_time)
        if Bus.voltage_flag == 0:
            sender_task = asyncio.create_task(self.sender())
            await sender_task
        else:
            await self.wait_util_free()
            sender_task = asyncio.create_task(self.sender())
            await sender_task

    async def collision_handler(self):
        message = f"{self.name} send collision"

        Bus.voltage_flag -= 1
        self.collision_timer -= 1
        if self.collision_timer == 0:
            logging.info(message)
            logging.info(f"{self.name} send failed")
            self.update_timer_on_failure()
            return 1

        backoff_time = self.get_backoff_time(self._max_collision_endure - self.collision_timer)

        message += f", backoff for {backoff_time}s"
        logging.info(message)

        await asyncio.sleep(backoff_time)
        return 0

    async def sender(self):
        self.send_ok = 0

        await asyncio.sleep(0.00096)
        while self.send_ok == 0:
            Bus.voltage_flag += 1
            for i in range(len(self.data)):
                if Bus.voltage_flag == 1:
                    Bus.data[i] = self.data[i]
                    await asyncio.sleep(0.00001)
                elif Bus.voltage_flag == 2:
                    fail_flag = await self.collision_handler()
                    if fail_flag:
                        return
                    else:
                        break
                else:
                    logging.info("sending not activate")

                if i == len(self.data) - 1:
                    self.validate_sending()


client_a = Client("Client A")
client_b = Client("Client B")


async def report_work():
    await asyncio.gather(client_a.report(),
                         client_b.report())

    while client_a.data == client_b.data:
        await asyncio.gather(client_a.report(),
                             client_b.report())


async def send_work():
    while client_a.global_timer != 5 and client_b.global_timer != 5:
        await asyncio.gather(client_a.send(),
                             client_b.send())


def clear_log():
    os.remove("./running.log")


if __name__ == '__main__':
    clear_log()
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s',
                        handlers=[
                            logging.FileHandler("./running.log"),
                            logging.StreamHandler()
                        ])

    start_time = time.time()

    asyncio.run(report_work())
    asyncio.run(send_work())
    asyncio.run(report_work())

    finish_time = time.time()
    logging.info(f"finished in {finish_time - start_time}s")
