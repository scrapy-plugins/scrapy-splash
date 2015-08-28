sub = string.sub
find = string.find
upper = string.upper
lower = string.lower

function parse_viewport(viewport)
    -- Splash lua has no regex support, if added, /\d+x\d+/
    local sep = find(viewport, "x")
    if sep then
        local width = tonumber(sub(viewport, 1, sep-1))
        local height = tonumber(sub(viewport, sep+1, #viewport))
        if width and height then
            return {width, height}
        end
    end
    return nil
end

-- x-FOO-bAr -> X-Foo-Bar
function normalize_header(name)
    name = upper(sub(name, 1, 1)) .. lower(sub(name, 2))
    while true do
        local start,fin = find(name, '-[a-z]')
        if start ~= nil then
            name = sub(name, 1, start) .. upper(sub(name, fin, fin)) .. sub(name, fin+1)
        else
            break
        end
    end
    return name
end

function normalize_headers(headers)
    local res = {}
    for name,value in pairs(headers) do
        res[normalize_header(name)] = value
    end
    return res

end

function main(splash)
    local args = splash.args
    local crawlera = args.crawlera or {}
    local host = crawlera.host or 'proxy.crawlera.com'
    local port = crawlera.port or 8010
    local subrequest_headers = normalize_headers(crawlera.subrequest_headers or {})
    local allrequest_headers = normalize_headers(crawlera.headers or {})

    local session_header = "X-Crawlera-Session"
    local session_id = "create"

    if splash.on_response_headers == nil then
        error("Splash 1.7 is required for Crawlera integration")
    end

    splash:on_request(function (request)
        if session_id ~= 'create' then
            -- Set subresource request headers
            for name, value in pairs(subrequest_headers) do
                request:set_header(name, value)
            end
        end
        for name, value in pairs(allrequest_headers) do
            request:set_header(name, value)
        end

        -- Implement resource_timeout parameter like in render.html
        if type(args.resource_timeout) == 'number' then
            request:set_timeout(args.resource_timeout)
        end

        request:set_header(session_header, session_id)
        request:set_proxy{host, port, username=crawlera.user, password=crawlera.pass}
    end)

    splash:on_response_headers(function (response)
        for name, value in pairs(response.headers) do
            name = normalize_header(name)
            if name == session_header then
                session_id = value
            elseif name == "Retry-After" or sub(name, 1, 11) == 'X-Crawlera-' then
                splash:set_result_header(name, value)
            end
        end
    end)

    -- Implement some of the arguments to render.html
    if type(args.viewport) == 'string' then
        local width, height = parse_viewport(args.viewport)
        if width and height then
            splash:set_viewport_size(width, height)
        end
    end

    local ok, err = splash:go{args.url, baseurl=args.baseurl, headers=args.headers}
    if not ok then
        -- Send crawleras response code with the response if possible
        if sub(err, 1, 4) == "http" and splash.set_result_status_code ~= nil then
            splash:set_result_status_code(tonumber(sub(err, 5, 7)))
        else
            error('Splash error ' .. err)
        end
    end

    if args.viewport == 'full' or args.render_all then
        splash:set_viewport_full()
    end

    if type(args.wait) == 'number' then
        splash:wait(args.wait)
    end

    if type(args.js_source) == 'string' then
        splash:runjs(args.js_source)
    end

    splash:set_result_content_type("text/html; charset=utf-8")

    return splash:html()
end
