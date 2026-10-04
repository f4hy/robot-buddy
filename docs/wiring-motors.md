# M2 — Wiring the TB6612 to the battery and motors

The Pi-to-TB6612 signal wires are already done (pin map in
[DESIGN.md](DESIGN.md#pin-map)). This guide adds the last three groups: ground,
motor power, and the two motors.

**Do all of this with everything off:** Pi unplugged from the power bank, and
the battery box switch off (or batteries out).

## The TB6612 board

Most TB6612FNG breakouts (SparkFun and the common red/purple clones) have two
rows of 8 pins. The order varies, so go by the printed labels.

**The header pins must be soldered to the board.** They usually ship loose
(two pin strips with black spacers). Resting the board on unsoldered pins
makes no reliable contact, so nothing moves, even though it looks plugged in.
To solder them, push the long ends into the breadboard, sit the board on the
short ends, and solder from above; the breadboard keeps everything straight.

| Group          | Pins                         | Goes to                          |
| -------------- | ---------------------------- | -------------------------------- |
| Pi signals     | AIN1 AIN2 PWMA BIN1 BIN2 PWMB STBY | Pi GPIOs (done)            |
| Logic power    | VCC                          | Pi 3.3 V, pin 17 (done)          |
| Motor power    | VM                           | AA battery **+** (through the switch) |
| Ground         | GND (2–3 pins, all joined on the board) | Pi GND **and** AA battery **−** |
| Motor outputs  | AO1 AO2                      | Left motor's two wires           |
|                | BO1 BO2                      | Right motor's two wires          |

## Battery and switch

The switch goes on the battery's red (+) wire only. Black (−) goes straight to
ground.

```
 AA box red (+) ──► switch ──► battery (+) rail ──► TB6612 VM
 AA box black (−) ───────────► battery (−) rail ──► TB6612 GND (+ Pi GND)
```

- **2-pin switch** (most rockers): red to one pin, the other pin to the (+)
  rail. Either way round.
- **3-pin switch** (most slide switches): middle pin plus one outer pin; leave
  the other outer pin empty. Red to the middle, outer pin to the (+) rail.
- **Battery box with a built-in switch:** skip the chassis switch; red goes
  straight to the (+) rail.

Joining wires: solder and heat-shrink is best on a robot that bumps into
things. Without an iron, hook the stripped wire through the tab, twist it tight
and tape it (fine for bench tests). Stranded battery wire is too floppy for a
breadboard: twist it onto a male jumper and cover the joint, crimp a male pin
on, or use a lever connector.

Check before connecting VM: on continuity mode, red wire to (+) rail beeps
only with the switch on. With batteries in and the switch on, the (+) rail
reads about 6 V against (−) (about 4.8 V with rechargeable NiMH).

## Breadboard layout

Seat the board across the centre gap, so each pin gets its own 5-hole column.
Use one power rail pair for the battery only.

```
   battery rail  (+) ─────────────────────────────────────────  ← AA + via switch
   battery rail  (−) ─────────────────────────────────────────  ← AA −
                  │                      │
                  │ (jumper)             │ (jumper)
                  ▼                      ▼
               ┌──────────────────────────────────┐
     row A:    │ VM  VCC  GND  AO1 AO2 BO2 BO1 GND│   ← labels on your board may differ
               │          TB6612FNG               │
     row B:    │PWMA AIN2 AIN1 STBY BIN1 BIN2 PWMB GND
               └──────────────────────────────────┘
                     ▲              ▲
                     └── Pi wires (done) ──┘
```

Wire it like this:

1. **Ground.** Battery − to the battery (−) rail. A jumper from that rail to a
   TB6612 GND pin. Then a wire from another TB6612 GND pin to a Pi GND (pin 6
   or 9). This shared ground is required: without it, the Pi's signals have
   no reference and the motors twitch or do nothing.
2. **Motor power.** Battery + (the red wire, after the chassis switch) to the
   battery (+) rail. A jumper from that rail to **VM**.
3. **Left motor.** Its two wires to AO1 and AO2. Use the breadboard holes in
   the same column as each pin. Order doesn't matter.
4. **Right motor.** Its two wires to BO1 and BO2.

If the motor leads are bare stranded wire, twist the strands tight or crimp on
a pin. Loose strands short neighbouring columns. If the motors have no leads,
they need wires soldered to their tabs.

Optional: a 100 µF electrolytic capacitor across VM and GND, close to the
board (long leg to VM), smooths motor spikes. Nice to have, not required.

## Check before powering on

- [ ] Battery + goes **only** to VM. Nothing from the battery touches the Pi's
      5 V or 3.3 V pins.
- [ ] VCC goes to Pi **3.3 V** (pin 17), not 5 V.
- [ ] Battery −, TB6612 GND and Pi GND are all connected.
- [ ] The (+) battery rail has nothing on it except the battery and VM.
- [ ] No bare wire ends touching each other.
- [ ] Long breadboards sometimes split each rail in the middle; if yours has a
      gap in the red/blue line, bridge it or stay on one half.

## Power on and test

1. Prop the chassis up so both wheels spin freely.
2. Power the Pi from the power bank and wait for SSH (a minute or two after
   the first boot).
3. Turn the battery switch on. Nothing should move: the Pi's direction pins
   default to low, so the driver stays stopped.
4. Run the bench test:

   ```sh
   ssh robot@192.168.1.213
   python3 ~/robot_buddy/scripts/check_motors.py
   ```

5. It spins the left wheel forward, then backward, then the right wheel the
   same way.

| You see                                  | Fix |
| ---------------------------------------- | --- |
| A wheel turns backward when it says forward | Set that side's `invert: true` in `config/robot.yaml` |
| The right wheel moves when it says left  | Swap the `left` and `right` pin sets in `config/robot.yaml` |
| Nothing moves                            | Battery switch on? Shared GND wired? STBY on pin 29? Check `vcgencmd get_throttled` |
| One wheel never moves                    | Check that motor's two wires and its PWM wire (PWMA pin 18 / PWMB pin 22) |
| Pi reboots when the motors start         | Battery wired to the Pi by mistake, or the power bank is weak; recheck the first item above |

M2 is done when each wheel spins forward and backward in the right direction.
