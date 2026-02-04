close all; fclose('all'); clear all; clc

% ---------------------------------------------------------------
% USER SETTINGS
% ---------------------------------------------------------------
exppath = '/scratch/apatil5/nominalles/';  % base path to experiments
start_exp_number = 1                % Starting number of the experiment
end_exp_number = 10                 % End number of the experiment
dist_fix = 0.5;                     % replacement for zero or NaN distances
area_fix = 0.25;                    % replacement for zero or NaN areas
% ---------------------------------------------------------------
for expnr = start_exp_number:end_exp_number  
    expstr = sprintf('%03d',expnr);
    fpath = [exppath expstr];
    fprintf('\n=== Processing Experiment %s ===\n', expstr);

    files = {
        'facet_sections_u.txt'
        'facet_sections_v.txt'
        'facet_sections_w.txt'
        'facet_sections_c.txt'
    };

    for i = 1:length(files)
        fname = fullfile(fpath, files{i});
        fprintf('\nProcessing %s ...\n', files{i});
        fix_facetsections_format_preserving(fname, dist_fix, area_fix);
    end

    fprintf('\nAll facet_sections_* files processed.\n');
    fclose('all');   
end

% =================================================================
% FUNCTION: FIX FILE WHILE PRESERVING COLUMN FORMAT
% =================================================================
function fix_facetsections_format_preserving(filename, dist_fix, area_fix)

    % Read entire file as text lines
    fid = fopen(filename, 'r');
    if fid < 0
        error('Could not open %s', filename);
    end

    lines = {};
    while ~feof(fid)
        lines{end+1} = fgetl(fid);
    end
    fclose(fid);

    % Prepare output
    fid = fopen(filename, 'w');

    for i = 1:length(lines)
        line = lines{i};

        % Skip empty lines
        if isempty(line)
            fprintf(fid, '\n');
            continue
        end

        % Preserve header lines (non-numeric)
        if startsWith(strtrim(line), "#")
            fprintf(fid, '%s\n', line);
            continue
        end

        % Convert line into numbers (4 columns expected)
        vals = sscanf(line, '%f');

        if numel(vals) ~= 4
            % Unexpected format -- write as-is
            fprintf(fid, '%s\n', line);
            continue
        end

        facet     = vals(1);
        area      = vals(2);
        fluxpoint = vals(3);
        dist      = vals(4);

        % Fix values
        if area == 0 || isnan(area)
            area = area_fix;
        end
        if dist == 0 || isnan(dist)
            dist = dist_fix;
        end

        % Write back in EXACT format (aligned like your example)
        fprintf(fid, '%8d %10.4f %10d %10.4f\n', facet, area, fluxpoint, dist);
    end

    fclose(fid);

    fprintf('Fixed and preserved formatting: %s\n', filename);
end
