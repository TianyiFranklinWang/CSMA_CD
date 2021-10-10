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
        self.name = name
        self.data = str(random.randrange(10000, 99999))
        self.success_timer = 0
        self.collision_timer = 16

    async def report(self):
        message = f"\ndata:               {self.data}\n" \
                  f"success_timer:      {self.success_timer}\n" \
                  f"collision_timer:    {self.collision_timer}\n"
        logging.info(message)

    def reset_all(self):
        self.data = str(random.randrange(10000, 99999))
        self.success_timer = 0
        self.collision_timer = 16

    def reset_collision_timer(self):
        self.collision_timer = 16

    def get_data(self):
        self.data = str(random.randrange(10000, 99999))

    async def wait_util_free(self):
        while Bus.voltage_flag != 0:
            await asyncio.sleep(0.0001)

    async def starter(self):
        start_time = random.randrange(1, 96) / 100000
        if Bus.voltage_flag == 0:
            await asyncio.sleep(start_time)
            if Bus.voltage_flag == 0:
                send_task = asyncio.create_task(self.send())
                await send_task
            else:
                await self.wait_util_free()
                send_task = asyncio.create_task(self.send())
                await send_task
        else:
            await self.wait_util_free()
            send_task = asyncio.create_task(self.send())
            await send_task

    async def send(self):
        await asyncio.sleep(0.00096)
        send_ok = 0
        while send_ok == 0:
            Bus.voltage_flag += 1
            for i in range(len(self.data)):
                if Bus.voltage_flag == 1:
                    Bus.data[i] = self.data[i]
                    await asyncio.sleep(0.00001)
                elif Bus.voltage_flag == 2:
                    logging.info(f"{self.name} send collision")
                    Bus.voltage_flag -= 1
                    self.collision_timer -= 1
                    if self.collision_timer == 0:
                        logging.info(f"{self.name} send failed")
                        return
                    backoff_time = self.binary_exponential_backoff(16 - self.collision_timer)
                    await asyncio.sleep(backoff_time)
                    break
                else:
                    logging.info("sending not activate")

                if i == len(self.data) - 1:
                    Bus.voltage_flag -= 1
                    bus_data = ''
                    for i in range(len(Bus.data)):
                        bus_data += Bus.data[i]
                    if bus_data == self.data:
                        logging.info(f"{self.name} send success")
                        self.success_timer += 1
                        self.reset_collision_timer()
                        send_ok = 1
                    else:
                        logging.info(
                            f"{self.name} send failed, bus_data: {bus_data} not correspond to self.data: {self.data}")

    def binary_exponential_backoff(self, time):
        k = time if time <= 10 else 10
        r = random.randrange(0, 2 ** k - 1)
        return r * 0.00512


client_a = Client("Client A")
client_b = Client("Client B")


async def report_work():
    logging.info(f"start at {time.strftime('%X')}")
    await asyncio.gather(client_a.report(),
                         client_b.report())
    while client_a.data == client_b.data:
        await asyncio.gather(client_a.report(),
                             client_b.report())


async def send_work():
    while client_a.success_timer != 5 and client_b.success_timer != 5:
        await asyncio.gather(client_a.starter(),
                             client_b.starter())
    logging.info(f"finish at {time.strftime('%X')}")


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
