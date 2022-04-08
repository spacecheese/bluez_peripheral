# Running Unit Tests
Install the test dependencies
```bash
pip install -r requirements.txt
```
Add the dbus config to allow the test process access to the bluetooth daemon.
> This has serious security implications so only do this if you know what you are doing.
```bash
sudo cp com.spacecheese.test.conf /etc/dbus-1/system.d
```