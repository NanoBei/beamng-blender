dofile('/art/china_subject2_v1/load.lua')
local v=assert(be:getPlayerVehicle(0),'Player vehicle missing')
spawn.safeTeleport(v,vec3(-1691,-1490,101.4),quatFromDir(vec3(1,0,0)),nil,nil,nil,nil,true)
core_camera.setByName(0,'orbit')
return 'Subject 2 exam entrance'
