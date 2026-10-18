function run_figures_4_5_6(fig)
%RUN_FIGURES_4_5_6 Generate Figures 4, 5, or 6 as PNG.
%
%   run_figures_4_5_6(4)  -> Fed Chair Speech
%   run_figures_4_5_6(5)  -> Fed Interviews Top 100
%   run_figures_4_5_6(6)  -> Fed Interviews Top 200
%
%   Inputs are read from Data/figure4_6/ and outputs are written to
%   Figures/figure<N>/ and Data/figure4_6/, both relative to the package root.
%
%   Estimation is deterministic: the starting point is inv(chol(cov(Y)))
%   with no random perturbation, so no seed is required.
%
%   Depends: nlogl_iidstudent_Wzn.m (-> kr.m) from Code/common/matlab,
%            plot_resp.m from this directory.

switch fig
    case 4
        data_file = "reg_baha_powell_79.csv";
    case 5
        data_file = "reg_interview_top100_without200402.csv";
    case 6
        data_file = "reg_interviews_top200.csv";
    otherwise
        error("fig must be 4, 5, or 6");
end

scriptDir = fileparts(mfilename("fullpath"));
packageRoot = fileparts(fileparts(scriptDir));
addpath(fullfile(packageRoot, "Code", "common", "matlab"));

dataPath = fullfile(packageRoot, "Data", "figure4_6", data_file);
figDir = fullfile(packageRoot, "Figures", sprintf("figure%d", fig));
dataOutDir = fullfile(packageRoot, "Data", "figure4_6");
if ~exist(figDir, "dir"), mkdir(figDir); end
if ~exist(dataOutDir, "dir"), mkdir(dataOutDir); end

ttab = readtimetable(dataPath);
ttab.date.Format = "uuuu-MM-dd";

ynames = ["TFUT02", "SP500"];
ymaturities = [2 NaN];

indmissing = logical(sum(isnan(ttab{:, ynames}), 2));
if any(indmissing)
    fprintf("dropping %d observations with missing values\n", sum(indmissing));
    ttab(indmissing, :) = [];
end

Y = ttab{:, ynames};
[T, N] = size(Y);

options = optimoptions("fmincon");
options.Display = "iter";
options.MaxFunctionEvaluations = 1e4 * N^2;
options.OptimalityTolerance = 1e-9;
options.Algorithm = "trust-region-reflective";
options.SpecifyObjectiveGradient = true;

A = []; b = []; Aeq = []; beq = [];
lb = [repmat(-Inf, N^2, 1); repmat(0, N, 1)];
ub = []; nonlcon = [];

W = inv(chol(cov(Y)));
par0 = [W(:); repmat(log(3), N, 1)];

fun = @(par) nlogl_iidstudent_Wzn(Y, reshape(par(1:N^2), N, N), par(N^2+1:end));
[parmaxlik, fval, ~, ~, ~, ~, hessian] = fmincon(fun, par0, A, b, Aeq, beq, lb, ub, nonlcon, options);

W = reshape(parmaxlik(1:N^2), N, N);
C = inv(W);
v = exp(parmaxlik(N^2+1:end));

P = diag(sign(mean(C(:, ~isnan(ymaturities)), 2)));
idx = nan(1, N);
temp = abs(C);
for n = 1:N
    [~, i] = max(temp(:, n));
    idx(n) = i;
    temp(i, :) = -inf;
end
P = P(idx, :);

Wnormalized = W * P';
vnormalized = abs(P) * v;
par0 = [Wnormalized(:); log(vnormalized)];
[parmaxlik, fval, ~, ~, ~, ~, hessian] = fmincon(fun, par0, A, b, Aeq, beq, lb, ub, nonlcon, options);

maxl.Y = Y;
maxl.ll = -fval;
maxl.parmaxlik = parmaxlik;
maxl.hessian = hessian;
maxl.v = exp(parmaxlik(N^2+1:end));
maxl.W = reshape(parmaxlik(1:N^2), N, N);
maxl.C = inv(maxl.W);
maxl.U = Y * maxl.W;
maxl.U1s = maxl.U ./ std(maxl.U);
maxl.C1s = diag(std(maxl.U)) * maxl.C;
maxl.vdec = (maxl.C1s.^2) ./ sum(maxl.C1s.^2);
temp = diag(diag(maxl.C(:, [1 1])));
maxl.C1bp = temp \ maxl.C;
maxl.U1bp = maxl.U * temp;

save(fullfile(dataOutDir, sprintf("figure%d_maxl.mat", fig)), "maxl");

JacobianWC = -kron(maxl.W', maxl.W);
Jacobianzv = diag(maxl.v.^-1);
JacobianWCzv = blkdiag(JacobianWC, Jacobianzv);
asyvarCv = inv(JacobianWCzv' * hessian * JacobianWCzv);
asystdCv = sqrt(diag(asyvarCv));
Cstd = reshape(asystdCv(1:N^2), N, N);

Cm = maxl.C;
Cl = Cm - 2 * Cstd;
Cu = Cm + 2 * Cstd;

fh = plot_resp(diag(std(maxl.U)) * Cm, diag(std(maxl.U)) * Cl, ...
    diag(std(maxl.U)) * Cu, ymaturities, ...
    variableNames=ynames, RowLabels="u" + (1:N), showTitles=false);

pngPath = fullfile(figDir, sprintf("figure%d_full.png", fig));
print(fh, pngPath, "-dpng", "-r300");
fprintf("wrote %s\n", pngPath);

% Close the figure so repeated calls in one MATLAB session do not accumulate
% open figures, which can invalidate the handle passed to print.
close(fh);

end
