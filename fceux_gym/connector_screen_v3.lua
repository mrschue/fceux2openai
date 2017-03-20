local socket = require("socket")


local clock = os.clock;
function sleep(n)
	local t0 = clock()
	while clock() - t0 <= n do end
end

function copy(source, dest)
	for key, value in pairs(source) do
		dest[key] = value
	end
end

function contains(set, key)
	return set[key] ~= nil
end

function translate(msg, control)
	press = true
	if string.char(string.byte(msg, 1)) ~= "p" then
		press = false
	end
	button = button_map[string.char(string.byte(msg, 2))]
	if button ~= nil then
		control[button] = press
	end
end

function control_emu(msg)
	F = control_map[string.char(string.byte(msg, 2))]
	if F ~= nil then
		F(string.char(string.byte(msg, 3)))
	else
		emu.message("Invalid command")	
	end
end

function interpret(msg, control)
	if string.char(string.byte(msg, 1)) == "c" then
		control_emu(msg)	
	else
		translate(msg, control)
	end
end

function load_state(slot)
	slot = tonumber(slot)
	if slot == 0 then
		slot = 10
	end
	state = savestate.object(slot)
	savestate.load(state)
	-- Reset controls
	copy(T, control)
	emu.frameadvance()
end

function advance_frames(n_frames)
	for i=0,n_frames do
		emu.frameadvance()
	end
end

function soft_reset(dummy)
	emu.softreset()
end

function transmit_memory(block_id)
	mem = memory.readbyterange(tonumber(block_id)*256, 256)
	connection_ram:send(PRE..mem..POST)
end

function transmit_observation(dummy)
	screen = gui.gdscreenshot() 
	connection_screen:send(PRE..screen..POST)
end

function advance(n_frames)
	for idx=0,n_frames do
		emu.frameadvance()
	end
end

function set_invincible(switch)
	if tonumber(switch) == 0 then
		currently_invincible = false
	elseif tonumber(switch) == 1 then
		currently_invincible = true
	end
end

function write_memory(address, wbyte)
	memory.writebyte(tonumber(address), tonumber(wbyte))
end
	

-- CONFIG
emu.speedmode("maximum")

-- EMU CONTROL MAPPING
control_map = {
	S = emu.softreset,
	A = advance,
	L = load_state,
	M = transmit_memory,
	V = transmit_observation,
	I = set_invincible
}

-- CONSTANTS
button_map = {u = "up", l = "left", d = "down", r = "right", A = "A", B = "B", t = "start", e = "select"}
PRE = ''
POST = ''
T = {}
T["up"] = false
T["down"] = false
T["left"] = false
T["right"] = false
T["A"] = false
T["B"] = false
T["start"] = false
T["select"] = false
control = {}
copy(T, control)
print("Test1")
emu.message("Test2")

--------------------------------------------------

currently_invincible = false

local host = '*'
local udp_port = 9788
local tcp_port_screen, tcp_port_ram = 9799, 9798

local udp = assert(socket.udp())
local tcp_server_screen = assert(socket.bind(host, tcp_port_screen))
local tcp_server_ram = assert(socket.bind(host, tcp_port_ram))

print(tcp_server_screen:getsockname())
print(tcp_server_ram:getsockname())

udp:setsockname(host, udp_port)
udp:settimeout(1)

tcp_server_screen:settimeout(10)
tcp_server_ram:settimeout(10)

emu.message("UDP Connect active")
emu.frameadvance();

emu.message("Waiting for screen TCP connection on port "..tcp_port_screen)
emu.frameadvance();
connection_screen = tcp_server_screen:accept()
if connection_screen ~= nil then
	emu.message("Screen TCP connection established")
	-- Send initial observation
	emu.frameadvance();
else
	emu.message("No TCP connection!")
end

emu.message("Waiting for RAM TCP connection on port "..tcp_port_ram)
emu.frameadvance();
connection_ram = tcp_server_ram:accept()

if connection_ram ~= nil then
	emu.message("RAM TCP connection established")
	emu.frameadvance();
else
	emu.message("No TCP connection!")
end

emu.message("Starting loop")

connection_screen:settimeout(2)
connection_ram:settimeout(2)

while (true) do
	B = udp:receive()
	if B ~= nil then
		interpret(B, control)
		joypad.set(1, control)
	end		
	if currently_invincible then
		write_memory(0x004B, 0x02)
	end
end;

