function run_figure3(seed)
%RUN_FIGURE3 Estimate FOMC announcement shocks and generate Figure 3.
%
%   run_figure3()      uses the default seed (0)
%   run_figure3(seed)  uses an explicit seed for the random starting point
%
%   Estimates Y = UC with Student-t shocks and unknown degrees of freedom v,
%   parameterized in terms of W and z, where YW = U, C = inv(W), v = exp(z).
%   Estimation is by maximum likelihood.
%
%   Adapted from code/matlabv1/main0_maxlik.m. The math is unchanged; paths
%   are now relative to the package root and the random starting point is
%   seeded so the run is reproducible.
%
%   Depends: nlogl_iidstudent_Wzn.m (-> kr.m) from Code/common/matlab,
%            normalize1.m and plot_resp.m from this directory.

if nargin < 1
    seed = 0;
end

scriptDir = fileparts(mfilename("fullpath"));
packageRoot = fileparts(fileparts(scriptDir));
addpath(fullfile(packageRoot, "Code", "common", "matlab"));

dataPath = fullfile(packageRoot, "Data", "figure3", "reg_fomc_announcement.csv");
figDir = fullfile(packageRoot, "Figures", "figure3");
outDir = fullfile(packageRoot, "Data", "figure3");
if ~exist(figDir, "dir"), mkdir(figDir); end

tab = readtable(dataPath);
tab.date.Format = "uuuu-MM-dd";

fprintf("Data from %s to %s, T=%d\n", tab{1, "date"}, tab{end, "date"}, size(tab, 1));

ynames = {'MP1', 'TFUT02', 'TFUT10', 'SP500'};
Y = tab{:, ynames};
ymaturities = [1/12 2 10 NaN];
[T, N] = size(Y);

% Maximum likelihood / posterior mode estimation of W(->C), z(->v)
options = optimoptions("fminunc");
options.Display = "iter";
options.MaxFunctionEvaluations = 1e4 * N^2;
options.OptimalityTolerance = 1e-8;
options.Algorithm = "trust-region";
options.SpecifyObjectiveGradient = true;

% Starting point. The original script perturbed chol(cov(Y)) by randn(N,N)
% without setting a seed, which made the run non-reproducible. The seed is
% now explicit.
rng(seed, "twister");
W = inv(chol(cov(Y)) + randn(N, N));
par0 = [W(:); repmat(log(3), N, 1)];

fun = @(par) nlogl_iidstudent_Wzn(Y, reshape(par(1:N^2), N, N), par(N^2+1:end));
[parmaxlik, fval, ~, ~, ~, hessian] = fminunc(fun, par0, options);
W = reshape(parmaxlik(1:N^2), N, N);
C = inv(W);
v = exp(parmaxlik(N^2+1:end));

% Normalize
% 1. Sign: positive interest rate shock
% 2. Order by the maximum impact on consecutive variables
P = normalize1(C, ~isnan(ymaturities));

Wnormalized = W * P';
vnormalized = abs(P) * v;

% Minimize again to get the reordered hessian
par0 = [Wnormalized(:); log(vnormalized)];
[parmaxlik, fval, ~, ~, ~, hessian] = fminunc(fun, par0, options);

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
if N == 4, temp = [1 2 3 2]; else, temp = [1 1]; end
temp = diag(diag(maxl.C(:, temp)));
maxl.C1bp = temp \ maxl.C;
maxl.U1bp = maxl.U * temp;

disp("C"), disp(maxl.C)
disp("C1s"), disp(maxl.C1s)
disp("C1bp"), disp(maxl.C1bp)
disp("vdec"), disp(maxl.vdec)
disp("v"), disp(maxl.v)

save(fullfile(outDir, "figure3_maxl.mat"), "maxl");
writetable([tab(:, "date"), array2table(round(maxl.U, 5))], ...
    fullfile(outDir, "figure3_U.csv"));
writetable([tab(:, "date"), array2table(round(maxl.U1s, 5))], ...
    fullfile(outDir, "figure3_U1s.csv"));
writetable([tab(:, "date"), array2table(round(maxl.U1bp, 5))], ...
    fullfile(outDir, "figure3_U1bp.csv"));

% Variance of C, v
JacobianWC = -kron(maxl.W', maxl.W);
Jacobianzv = diag(maxl.v.^-1);
JacobianWzCv = blkdiag(JacobianWC, Jacobianzv);
asyvarCv = inv(JacobianWzCv' * hessian * JacobianWzCv);
asystdCv = sqrt(diag(asyvarCv));
Cstd = reshape(asystdCv(1:N^2), N, N);
vstd = asystdCv(N^2+1:end);
disp(array2table([maxl.v vstd], ...
    "VariableNames", ["MLE", "asy-std"], "RowNames", "v" + (1:N)))

Cm = maxl.C;
Cl = Cm - 2 * Cstd;
Cu = Cm + 2 * Cstd;
fh = plot_resp(diag(std(maxl.U)) * Cm, diag(std(maxl.U)) * Cl, ...
    diag(std(maxl.U)) * Cu, ymaturities, ynames);

pngPath = fullfile(figDir, "figure3_full.png");
print(fh, pngPath, "-dpng", "-r300");
exportgraphics(fh, fullfile(figDir, "figure3_full.pdf"));
fprintf("wrote %s\n", pngPath);

end
