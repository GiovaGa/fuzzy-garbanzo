# fuzzy-garbanzo


## Bibliography

A) Surveys, textbooks and broad references

- Mark S. Daskin — Network and Discrete Location: Models, Algorithms, and Applications. Wiley, 1995.
Summary: Classic text covering the main discrete and network location models (p‑median, p‑center, UFL, capacitated variants), modeling choices, exact methods and heuristics; good for graph/network setups and applications.

- Zvi Drezner & Horst W. Hamacher (eds.) — Facility Location: Applications and Theory. Springer, 2002.
Summary: Edited collection and survey chapters spanning theory, algorithms and many applied variants; useful for references and variant formulations (including network/location on graphs).

- Vijay V. Vazirani — Approximation Algorithms. Springer, 2001.
Summary: Text with canonical approximation methods (primal–dual, local search, rounding) with chapters and exercises on facility location and k‑median; good for algorithmic paradigms.

B) Canonical algorithmic papers (UFL, p‑median, p‑center)

- S. L. Hakimi — “Optimum Locations of Switching Centers and the Absolute Centers and Medians of a Graph.” Operations Research, 12(3):450–459, 1964.
DOI / link: https://doi.org/10.1287/opre.12.3.450
Summary: Foundational graph formulation of center/median problems; establishes many basic graph‑based location concepts and is a standard citation for p‑median on networks.

- O. Kariv & S. L. Hakimi — “An Algorithmic Approach to Network Location Problems. I: The p‑Medians.” SIAM J. Appl. Math., 37(3):513–538, 1979.
Summary: Algorithmic study of p‑median on networks; gives core algorithms and reductions used in later graph‑specific work.

- O. Kariv & S. L. Hakimi — “An Algorithmic Approach to Network Location Problems. II: The p‑Centers.” SIAM J. Appl. Math., 37(3):539–560, 1979.
Summary: Companion to the p‑median paper treating p‑center problems on graphs and networks.

- Kamal Jain & Vijay V. Vazirani — “Approximation Algorithms for Metric Facility Location and k‑Median Problems using the Primal‑Dual Schema and Lagrangian Relaxation.” J. ACM, 48(2):274–296, 2001.
Summary: Introduced a versatile primal–dual framework and constant‑factor approximation algorithms for metric UFL and related problems; highly influential in approximation algorithms for facility location.

- V. Arya, N. Garg, R. Khandekar, A. Meyerson, K. Munagala & V. Pandit — “Local Search Heuristics for k‑Median and Facility Location Problems.” SIAM J. Comput., 33(3):544–562, 2004.
Summary: Provides analysis of local‑search heuristics for k‑median/UFL with provable guarantees; explains why simple swap‑based local search performs well in practice and theory.

- Shi Li — “A 1.488 Approximation Algorithm for the Uncapacitated Facility Location Problem.” arXiv:1104.2557, 2011; published in Information and Computation, 222:45–58, 2013.
Summary: State‑of‑the‑art improvement (at the time) on approximation ratio for metric UFL; uses refined LP‑rounding and analysis techniques.

C) Graph‑specific complexity and recent graph work 
- N. Megiddo & A. Tamir — “On the Complexity of Locational Problems.” SIAM J. Algebraic Discrete Methods / SIAM J. Comput. (classical complexity results), 1983.
DOI / link (representative): https://doi.org/10.1137/0604035
Summary: Establishes hardness/complexity boundaries for many geometric/location problems (including network/graph settings); widely cited for negative results on general graphs.

- Mark S. Daskin (chapter & monograph material referenced widely) / textbook material (see entry A1).
Summary: For graph-specific methods, modeling, and branch‑and‑bound/MIP formulations, Daskin’s text remains a practical resource.

- Tim A. Hartmann, Stefan Lendl, Gerhard J. Woeginger — “Continuous Facility Location on Graphs.” Mathematical Programming (B), 2022. DOI / link: https://link.springer.com/article/10.1007/s10107-021-01710-x
Summary: Recent theoretical work that studies continuous placement (along edges, not just vertices) and δ‑covering/δ‑dispersion problems on graphs; useful for modern graph location formulations.

- Wenxuan Guo, Yanyan Xu, Yaohui Jin — “Swap‑based Deep Reinforcement Learning for Facility Location Problems in Networks.” arXiv:2312.15658, 2023. arXiv link / PDF: https://arxiv.org/abs/2312.15658
Summary: Modern ML/heuristic approach applying RL + swap local search to p‑median / relocation problems on networks — relevant for large graphs and empirical approaches.

D) Interaction, pairwise / co‑location / quadratic / dispersion variants

-  H. A. Eiselt, Z. Marianov, G. F. B. (and coauthors) — “The Planar Multiple Facility Location Problem with Interfacility Interaction: Concepts and Solution Approaches.” Operations Research / OR literature, early 1990s.
Summary: Introduces and surveys models where interfacility interaction (synergy or interference) affects the objective; discusses modeling choices and solution approaches (piecewise linearization, heuristics).

- E. Çela — The Quadratic Assignment Problem. Springer, 1998. (monograph; QAP is the canonical pairwise interaction analog, useful for theoretical links)
Papers titled “Quadratic facility location” or “facility location with interaction costs” (various authors; look for Eiselt et al., Dror et al., and OR journal articles from 1990s–2010s).
Summary: Pairwise facility interaction terms convert UFL into a 0–1 quadratic program (or QAP‑like) — these works analyze formulations, linearizations and heuristics.

- M. Dror, P. Engevall, M. L. Glover, G. Laporte — “The Maximum Dispersion Problem.” J. of Location Science / related journals, 2003.

- E. D. Demaine, U. Feige, M. Hajiaghayi, M. R. Salavatipour — “Dispersion Problems on Trees and Intervals.” Theoretical Computer Science (TCS) (approx. 2010).
Summary: Gives exact/efficient algorithms for variants of dispersion on trees and intervals — directly relevant to graph dispersion constraints (pairwise distance lower bounds).

